$ErrorActionPreference = 'Stop'
$localDbCommand = Get-Item -LiteralPath 'C:\Program Files\Microsoft SQL Server\150\Tools\Binn\SqlLocalDB.exe' -ErrorAction SilentlyContinue
if (-not $localDbCommand) {
  $candidates = Get-ChildItem -LiteralPath 'C:\Program Files\Microsoft SQL Server' -Filter SqlLocalDB.exe -Recurse -ErrorAction SilentlyContinue
  $localDbCommand = $candidates | Sort-Object FullName -Descending | Select-Object -First 1
}
if (-not $localDbCommand) { throw 'Installed LocalDB runtime unavailable; no database attached.' }
$localDbPath = if ($localDbCommand.Source) { $localDbCommand.Source } else { $localDbCommand.FullName }
& $localDbPath versions
& $localDbPath create BrnoPublicAudit 15.0 -s
if ($LASTEXITCODE -ne 0) { throw 'LocalDB instance creation failed' }
$connection = [System.Data.SqlClient.SqlConnection]::new('Data Source=(localdb)\BrnoPublicAudit;Integrated Security=true;Initial Catalog=master;Connect Timeout=30;Encrypt=false')
try {
  $connection.Open()
  $command = $connection.CreateCommand()
  $command.CommandTimeout = 60
  $mdfPath = Join-Path $env:RUNNER_TEMP 'brno-public-source\BKLRSKPRCAMDLZ.MDF'
  $command.CommandText = "DBCC CHECKPRIMARYFILE (N'" + $mdfPath.Replace("'", "''") + "', 2) WITH NO_INFOMSGS"
  $reader = $command.ExecuteReader()
  while ($reader.Read()) {
    $row = [ordered]@{}
    for ($i = 0; $i -lt $reader.FieldCount; $i++) { $row[$reader.GetName($i)] = $reader.GetValue($i).ToString() }
    Write-Output ('BRNO_MDF_METADATA=' + ($row | ConvertTo-Json -Compress))
  }
  $reader.Close()
  # Only ephemeral copies are attached; no ETAP application, source SQL, views,
  # procedures, assemblies or computed columns are executed.
  $ldfPath = Join-Path $env:RUNNER_TEMP 'brno-public-source\BKLRSKPRCAMDLZ_log.LDF'
  $command.CommandText = "CREATE DATABASE [BrnoReadOnlyCopy] ON (FILENAME=N'" + $mdfPath.Replace("'", "''") + "'), (FILENAME=N'" + $ldfPath.Replace("'", "''") + "') FOR ATTACH"
  $command.ExecuteNonQuery() | Out-Null
  $command.CommandText = 'ALTER DATABASE [BrnoReadOnlyCopy] SET TRUSTWORTHY OFF; ALTER DATABASE [BrnoReadOnlyCopy] SET DB_CHAINING OFF; ALTER DATABASE [BrnoReadOnlyCopy] SET READ_ONLY;'
  $command.ExecuteNonQuery() | Out-Null
  $connection.ChangeDatabase('BrnoReadOnlyCopy')
  $command.CommandText = @'
SELECT s.name AS schema_name,t.name AS table_name,c.name AS column_name,
       ty.name AS type_name,c.max_length,c.precision,c.scale,c.is_computed,c.column_id
FROM sys.tables AS t JOIN sys.schemas AS s ON t.schema_id=s.schema_id
JOIN sys.columns AS c ON t.object_id=c.object_id
JOIN sys.types AS ty ON c.user_type_id=ty.user_type_id
WHERE t.is_ms_shipped=0 ORDER BY s.name,t.name,c.column_id
'@
  $adapter = [System.Data.SqlClient.SqlDataAdapter]::new($command)
  $schema = [System.Data.DataTable]::new()
  $adapter.Fill($schema) | Out-Null
  $tableGroups = $schema.Rows | Group-Object schema_name,table_name
  if ($tableGroups.Count -gt 2048) { throw 'Excessive physical table count' }
  $all = @()
  foreach ($group in $tableGroups) {
    $columns = @($group.Group | ForEach-Object {
      [ordered]@{name=$_.column_name;type=$_.type_name;length=$_.max_length;precision=$_.precision;scale=$_.scale;computed=$_.is_computed}
    })
    $schemaName = [string]$group.Group[0].schema_name
    $tableName = [string]$group.Group[0].table_name
    $qualified = '[' + $schemaName.Replace(']', ']]') + '].[' + $tableName.Replace(']', ']]') + ']'
    $command.CommandText = 'SELECT COUNT_BIG(*) FROM ' + $qualified
    $count = $command.ExecuteScalar()
    $record = [ordered]@{schema=$schemaName;table=$tableName;count=$count;columns=$columns}
    if ($count -gt 0) {
      Write-Output ('BRNO_MDF_TABLE=' + ($record | ConvertTo-Json -Depth 8 -Compress))
      $safeColumns = @($group.Group | Where-Object {
        -not $_.is_computed -and $_.type_name -in @('int','smallint','tinyint','bigint','bit','float','real','decimal','numeric','varchar','nvarchar','char','nchar') -and
        $_.column_name -notmatch 'password|token|license|credential|connectionstring|secret'
      })
      if ($safeColumns.Count -gt 0 -and $tableName -match 'xfmr|trans|breaker|relay|lvcb|hvcb|tcc|setting|study|case|power|util|bus|lump|static|load') {
        $columnSql = ($safeColumns | ForEach-Object { '[' + $_.column_name.Replace(']', ']]') + ']' }) -join ','
        $command.CommandText = 'SELECT TOP (2) ' + $columnSql + ' FROM ' + $qualified
        $sampleReader = $command.ExecuteReader()
        $samples = @()
        while ($sampleReader.Read()) {
          $row = [ordered]@{}
          for ($i=0; $i -lt $sampleReader.FieldCount; $i++) {
            $v = $sampleReader.GetValue($i)
            if ($v -is [System.DBNull]) { $v = $null }
            if ($v -is [string] -and $v.Length -gt 160) { $v = $v.Substring(0,160) }
            $row[$sampleReader.GetName($i)] = $v
          }
          $samples += $row
        }
        $sampleReader.Close()
        Write-Output ('BRNO_MDF_SAMPLE=' + (@{table=$tableName;rows=$samples} | ConvertTo-Json -Depth 8 -Compress))
      }
    }
    $all += $record
  }
  $recoveryFields = @{
    LVCB=@('IID','Revision','ID','FromElement','ToElement','InService','Status','ElectricalStandard','TypeOfBreaker','iecCurrent','iecVoltage','iecMaking','iecBreaking','IecServiceBreaking','Ithr','Tkr','TripDeviceType','TripDeviceTypeName','TripDeviceSizeID','TripDeviceModel','TripDeviceMFR','SstRatingPlug','SstPhLT','SstPhST','SstPhInst','SstGrd','SstPhLTPickup','SstPhLTBand','SstPhSTPickup','SstPhSTBand','SstPhInstPickup','SstGrdPickup','SstGrdBand','SstPhLTUnit','SstPhSTUnit','SstPhInstUnit','SstGrdUnit','sstPhSTI2t','SstGrdI2t','ThermalMagThermalTrip','ThermalMagMagTrip','ThermalMagGrdPickup','ThermalMagGrdTimeDelay')
    HVCB=@('IID','Revision','ID','FromElement','ToElement','InService','Status','iecMFR','iecType','iecVoltage','iecCurrent','iecBreaking','Ithr','Tkr')
    XFMR2=@('IID','Revision','ID','FromBus','ToBus','InService','PrimkV','SeckV','PrimConnectionButton','SecConnectionButton','PrimGroundingType','SecGroundingType','SecEarthingType','PrimEarthingType','SecNeutralConn','PrimNeutralConn','PhaseShiftPS','PhaseShiftHL','SecGroundingAmpers1','SecGroundingAmpers2','SecGroundingParallelX','SecGroundingParallelR','SecGroundingAmpersX','SecGroundingAmpersR','SecGroundingSecOhms','SecGroundingKVA','SecGroundingKV1','SecGroundingKV2','Grounded','PrimGrounded')
    Lump=@('IID','Revision','ID','InService','Bus','PhaseConnection','MVA','KV','PF','MTLoadPercent','LoadPercent0','LoadPercent1','LoadPercent2','ModelType','ConstantZPercent','MotorLoadPercent','StaticLoadPercent')
    StaticLoad=@('IID','Revision','ID','InService','Bus','PhaseConnection','KVA','KW','Kvar','PF','KV','Quantity','PercentLoad0','PercentLoad1','PercentLoad2','ModelType')
    LoadFlowProps=@('IID','Revision','ID','LoadingCategory','LoadingType','BoolFieldsLF','AdjustmentsLF','CableGlobalTemp','LineGlobalTemp','VoltageAngle','VoltageMagnitude')
    ShortCircuitProps=@('IID','Revision','ID','StandardType','PrefaultIEC230','PrefaultIECOther','PrefaultIEC1001','PrefaultIEC35000','MotorContribution','LoadingCategory','BoolFieldsSC','AdjustmentsSC','CableGlobalTemp','LineGlobalTemp','LumpLoadModel','IECIncludeMtrContrib','IECUseTkrTk')
  }
  $recovered = @{}
  foreach ($tableName in $recoveryFields.Keys) {
    $known = @($schema.Rows | Where-Object {$_.table_name -eq $tableName})
    $columns = @($recoveryFields[$tableName] | Where-Object {$_ -in $known.column_name})
    $columnSql = ($columns | ForEach-Object {'[' + $_.Replace(']',']]') + ']'}) -join ','
    $command.CommandText = 'SELECT TOP (4096) ' + $columnSql + ' FROM [dbo].[' + $tableName + '] ORDER BY [IID], [Revision]'
    $dataReader = $command.ExecuteReader()
    $rows = @()
    while ($dataReader.Read()) {
      $row = [ordered]@{}
      for ($i=0;$i -lt $dataReader.FieldCount;$i++) {
        $v = $dataReader.GetValue($i)
        if ($v -is [System.DBNull]) {$v=$null}
        if ($v -is [string]) {$v=$v.Trim()}
        $row[$dataReader.GetName($i)]=$v
      }
      $rows += $row
    }
    $dataReader.Close()
    $recovered[$tableName] = $rows
    Write-Output ('BRNO_RECOVERED=' + (@{table=$tableName;rows=$rows} | ConvertTo-Json -Depth 8 -Compress))
  }
  New-Item -ItemType Directory -Path outputs/brno-mdf -Force | Out-Null
  @{schema='BRNO_MDF_ENGINEERING_FIELDS_V1';tables=$recovered;field_validation_performed=$false;installation_validation_closed=$false} | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath outputs/brno-mdf/engineering-fields.json -Encoding utf8
  @{schema='BRNO_MDF_PHYSICAL_SCHEMA_V1';tables=$all;electrical_calculation_performed=$false;installation_validation_closed=$false} | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath outputs/brno-mdf/schema.json -Encoding utf8
} finally {
  $connection.Dispose()
  & $localDbPath stop BrnoPublicAudit -k
  & $localDbPath delete BrnoPublicAudit
}

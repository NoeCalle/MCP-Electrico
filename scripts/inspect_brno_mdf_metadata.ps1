$ErrorActionPreference = 'Stop'
$localDbCommand = Get-Command SqlLocalDB.exe -ErrorAction SilentlyContinue
if (-not $localDbCommand) {
  $candidates = Get-ChildItem -LiteralPath 'C:\Program Files\Microsoft SQL Server' -Filter SqlLocalDB.exe -Recurse -ErrorAction SilentlyContinue
  $localDbCommand = $candidates | Sort-Object FullName -Descending | Select-Object -First 1
}
if (-not $localDbCommand) { throw 'Installed LocalDB runtime unavailable; no database attached.' }
$localDbPath = if ($localDbCommand.Source) { $localDbCommand.Source } else { $localDbCommand.FullName }
& $localDbPath versions
& $localDbPath create BrnoPublicAudit -s
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
} finally {
  $connection.Dispose()
  & $localDbPath stop BrnoPublicAudit -k
  & $localDbPath delete BrnoPublicAudit
}

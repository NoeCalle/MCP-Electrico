$ErrorActionPreference = 'Stop'
$media = Join-Path $env:RUNNER_TEMP 'sql2019-public-audit'
New-Item -ItemType Directory -Path $media -Force | Out-Null
$bootstrap = Join-Path $media 'SQL2019-SSEI-Expr.exe'
Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/?linkid=866658' -OutFile $bootstrap -TimeoutSec 120
$signature = Get-AuthenticodeSignature -LiteralPath $bootstrap
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') { throw 'Invalid Microsoft bootstrap signature' }
Write-Output ('SQL2019_BOOTSTRAP_SHA256=' + (Get-FileHash -LiteralPath $bootstrap -Algorithm SHA256).Hash)
$downloadArgs = @('/ACTION=Download','/MEDIATYPE=LocalDB','/QUIET',('/MEDIAPATH=' + $media))
$process = Start-Process -FilePath $bootstrap -ArgumentList $downloadArgs -PassThru -WindowStyle Hidden
if (-not $process.WaitForExit(240000)) { $process.Kill(); throw 'Microsoft media download timed out' }
if ($process.ExitCode -ne 0) { throw ('Microsoft media download failed: ' + $process.ExitCode) }
$package = Get-ChildItem -LiteralPath $media -Filter SqlLocalDB.msi -Recurse | Select-Object -First 1
if (-not $package) { throw 'LocalDB 2019 MSI missing' }
$signature = Get-AuthenticodeSignature -LiteralPath $package.FullName
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') { throw 'Invalid Microsoft MSI signature' }
Write-Output ('SQL2019_MSI_SHA256=' + (Get-FileHash -LiteralPath $package.FullName -Algorithm SHA256).Hash)
$process = Start-Process msiexec.exe -ArgumentList @('/i',('"' + $package.FullName + '"'),'/qn','/norestart','IACCEPTSQLLOCALDBLICENSETERMS=YES') -PassThru -WindowStyle Hidden
if (-not $process.WaitForExit(180000)) { $process.Kill(); throw 'LocalDB setup timed out' }
if ($process.ExitCode -notin @(0,3010)) { throw ('LocalDB setup failed: ' + $process.ExitCode) }

param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$serverPath = Join-Path $repo 'server.py'
$pidPath = Join-Path $repo "local_data\server-$Port.pid"
if (-not (Test-Path -LiteralPath $pidPath)) { Write-Output 'MCP no iniciado.'; exit 0 }
$serverPid = [int](Get-Content -LiteralPath $pidPath)
$process = Get-CimInstance Win32_Process -Filter "ProcessId = $serverPid"
if ($process -and $process.CommandLine -and $process.CommandLine.Contains($serverPath)) {
    # Terminate the verified launcher and its Windows venv interpreter tree.
    & taskkill.exe /PID $serverPid /T /F | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo detener el proceso del MCP.' }
    Write-Output 'MCP detenido.'
} else {
    Write-Output 'El proceso del MCP ya terminó.'
}
Remove-Item -LiteralPath $pidPath

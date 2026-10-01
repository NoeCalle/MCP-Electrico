param([int]$Port = 8765)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repo '.venv\Scripts\python.exe'
$serverPath = Join-Path $repo 'server.py'
$dataDir = Join-Path $repo 'local_data'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Falta el entorno .venv. Instale el proyecto antes de iniciar el servidor.'
}
if ($Port -lt 1 -or $Port -gt 65535) { throw 'Puerto fuera de rango.' }
New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
$pidPath = Join-Path $dataDir "server-$Port.pid"
if (Test-Path -LiteralPath $pidPath) {
    $previousPid = [int](Get-Content -LiteralPath $pidPath)
    $previous = Get-CimInstance Win32_Process -Filter "ProcessId = $previousPid"
    if ($previous -and $previous.CommandLine -and $previous.CommandLine.Contains($serverPath)) {
        Write-Output "MCP ya iniciado: http://127.0.0.1:$Port/mcp (PID $previousPid)"
        exit 0
    }
}
$arguments = @('-X', 'utf8', ('"' + $serverPath + '"'), '--transport', 'streamable-http', '--port', "$Port")
$process = Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $dataDir -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $dataDir "server-$Port.out.log") -RedirectStandardError (Join-Path $dataDir "server-$Port.err.log")
$process.Id | Set-Content -LiteralPath $pidPath
$ready = $false
for ($attempt = 0; $attempt -lt 100; $attempt++) {
    Start-Sleep -Milliseconds 200
    $process.Refresh()
    if ($process.HasExited) {
        Remove-Item -LiteralPath $pidPath
        throw (Get-Content -LiteralPath (Join-Path $dataDir "server-$Port.err.log") -Raw)
    }
    $log = Get-Content -LiteralPath (Join-Path $dataDir "server-$Port.err.log") -Raw
    if ($log -match 'Uvicorn running on') { $ready = $true; break }
}
if (-not $ready) { throw 'El servidor no confirmó su arranque. Revise local_data.' }
Write-Output "MCP iniciado: http://127.0.0.1:$Port/mcp (PID $($process.Id))"

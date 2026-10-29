$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if ($workspace -ne 'D:\meeting\J26-IT-358') {
    throw 'This start script is restricted to the PP1 working copy.'
}
foreach ($port in @(3001, 8001)) {
    $probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
    try { $probe.Start() } finally { $probe.Stop() }
}
$python = Join-Path $workspace '.venv\Scripts\python.exe'
$launcher = Join-Path $workspace 'scripts\pp1.py'
& $python -I -B $launcher init-db
if ($LASTEXITCODE -ne 0) { throw 'PP1 database initialization failed.' }
$logs = Join-Path $workspace 'scratch\pp1-isolation'
$backend = Start-Process -FilePath $python -ArgumentList @('-I', '-B', 'scripts\pp1.py', 'backend') `
    -WorkingDirectory $workspace -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs 'backend.stdout.log') `
    -RedirectStandardError (Join-Path $logs 'backend.stderr.log') -PassThru
$frontend = Start-Process -FilePath $python -ArgumentList @('-I', '-B', 'scripts\pp1.py', 'frontend') `
    -WorkingDirectory $workspace -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs 'frontend.stdout.log') `
    -RedirectStandardError (Join-Path $logs 'frontend.stderr.log') -PassThru
[pscustomobject]@{ BackendLauncherPid = $backend.Id; FrontendLauncherPid = $frontend.Id } |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logs 'services.json')
Write-Output "PP1 starting: http://127.0.0.1:3001/crop-planning ; API http://127.0.0.1:8001"
Write-Output "Logs: $logs"

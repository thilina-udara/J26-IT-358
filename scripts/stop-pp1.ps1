$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
if ($workspace -ne 'D:\meeting\J26-IT-358') {
    throw 'This stop script is restricted to the PP1 working copy.'
}
$statePath = Join-Path $workspace 'scratch\pp1-isolation\services.json'
if (-not (Test-Path -LiteralPath $statePath)) {
    Write-Output 'No recorded PP1 background services.'
    return
}
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$snapshot = @(Get-CimInstance Win32_Process)
foreach ($property in $state.PSObject.Properties) {
    if ($property.Name -notin @('FrontendLauncherPid', 'BackendLauncherPid')) { continue }
    $serviceProcessId = [int]$property.Value
    $rootProcess = $snapshot | Where-Object { $_.ProcessId -eq $serviceProcessId }
    if (-not $rootProcess) { continue }
    if ($rootProcess.CommandLine -notlike "*$workspace\.venv\Scripts\python.exe*" -or
        $rootProcess.CommandLine -notmatch 'scripts[\\/]pp1\.py\s+(backend|frontend)') {
        Write-Warning "PID $serviceProcessId is not a verified PP1 launcher; left untouched."
        continue
    }
    $tree = [System.Collections.Generic.List[object]]::new()
    $tree.Add($rootProcess)
    for ($index = 0; $index -lt $tree.Count; $index++) {
        foreach ($child in $snapshot | Where-Object { $_.ParentProcessId -eq $tree[$index].ProcessId }) {
            $tree.Add($child)
        }
    }
    for ($index = $tree.Count - 1; $index -ge 0; $index--) {
        $record = $tree[$index]
        $current = Get-CimInstance Win32_Process -Filter "ProcessId=$($record.ProcessId)"
        if ($current -and $current.CreationDate -eq $record.CreationDate) {
            try {
                Stop-Process -Id $record.ProcessId -ErrorAction Stop
            } catch {
                # A parent can exit by itself as soon as its child is stopped.
                if (Get-Process -Id $record.ProcessId -ErrorAction SilentlyContinue) { throw }
            }
            Write-Output "Stopped PP1 PID $($record.ProcessId) ($($record.Name))."
        }
    }
}

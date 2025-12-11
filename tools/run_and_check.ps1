# Starts the debug uvicorn launcher in background, polls health endpoint, then runs node checker
$python = 'C:/Users/kevin/AppData/Local/Microsoft/WindowsApps/python3.13.exe'
$launcher = Join-Path $PSScriptRoot 'uvicorn_debug_launcher.py'

Write-Host "Starting uvicorn debug launcher..."
$proc = Start-Process -FilePath $python -ArgumentList $launcher -PassThru -WindowStyle Hidden

$healthUrl = 'http://127.0.0.1:8000/health'
$maxWait = 8
$waited = 0
$ok = $false
while ($waited -lt $maxWait) {
    Start-Sleep -Seconds 1
    try {
        $r = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 1
        if ($r -and $r.status -eq 'healthy') {
            Write-Host "Health OK"
            $ok = $true
            break
        }
    } catch {
        # ignore
    }
    $waited += 1
}

if (-not $ok) {
    Write-Host "Server did not become healthy within $maxWait seconds"
    if ($proc -and -not $proc.HasExited) { Write-Host "Server process is running (PID $($proc.Id))" }
    else { Write-Host "Server process exited" }
    exit 2
}

Write-Host "Running node checker..."
node .\frontend\tests\api\check_results.cjs

# Give window for logs
Start-Sleep -Seconds 2

# Stop server
Write-Host "Stopping server (Kill)"
if ($proc -and -not $proc.HasExited) { Stop-Process -Id $proc.Id -Force }
Write-Host "Done"

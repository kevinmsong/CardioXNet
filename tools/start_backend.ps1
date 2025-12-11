$pyPath = Join-Path $PSScriptRoot '..\\venv\\Scripts\\python.exe'
$launcher = Join-Path $PSScriptRoot 'uvicorn_launcher.py'
@"
import uvicorn
uvicorn.run('app.main:app', host='0.0.0.0', port=8000, reload=False, log_level='info')
"@ | Out-File -Encoding utf8 $launcher

Start-Process -NoNewWindow -FilePath $pyPath -ArgumentList $launcher
Write-Output "Backend start requested (launcher: $launcher)"

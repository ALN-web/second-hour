# One-command start on Windows: .\start.ps1   (add -Seed to reset demo data)
param([switch]$Seed)
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"
$py = if (Test-Path .venv\Scripts\python.exe) { ".venv\Scripts\python.exe" } else { "python" }
if ($Seed -or -not (Test-Path data\secondhour.db)) { & $py -m scripts.seed }
$mcp = Start-Process $py -ArgumentList "-m","app.mcp_server" -PassThru -NoNewWindow
Start-Sleep 2
$api = Start-Process $py -ArgumentList "-m","uvicorn","app.api:app","--host","127.0.0.1","--port","8000" -PassThru -NoNewWindow
try { Set-Location frontend; npm run dev } finally { Stop-Process -Id $mcp.Id,$api.Id -ErrorAction SilentlyContinue }

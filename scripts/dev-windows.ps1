param(
    [switch]$SkipPacs,
    [switch]$NoViewer
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$BootstrapScript = Join-Path $RepoRoot "backend\scripts\dev-bootstrap.ps1"
$KillPortsScript = Join-Path $RepoRoot "scripts\kill-ports.ps1"
$BackendPython = Join-Path $RepoRoot "backend\.venv\Scripts\python.exe"

Set-Location $RepoRoot

& powershell -NoProfile -ExecutionPolicy Bypass -File $BootstrapScript
& powershell -NoProfile -ExecutionPolicy Bypass -File $KillPortsScript

if (-not $SkipPacs) {
    $Docker = Get-Command docker -ErrorAction SilentlyContinue
    if ($Docker) {
        Write-Host "Starting PACS server..."
        & docker compose -f docker-compose.pacs.yml down --remove-orphans
        & docker compose -f docker-compose.pacs.yml up -d
        if ($LASTEXITCODE -eq 0) {
            Start-Sleep -Seconds 5
            Write-Host "PACS services started: Orthanc http://localhost:8042"
        } else {
            Write-Warning "PACS docker start failed; continuing HMS dev server."
        }
    } else {
        Write-Warning "Docker was not found; skipping PACS services."
    }
}

$BackendCommand = "powershell -NoProfile -ExecutionPolicy Bypass -Command `"Set-Location 'backend'; `$env:AUTO_DB_BOOTSTRAP='false'; `$env:PYTHONPATH='.'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`""
$FrontendCommand = "powershell -NoProfile -ExecutionPolicy Bypass -Command `"Set-Location 'frontend'; npm start`""
$ViewerCommand = "powershell -NoProfile -ExecutionPolicy Bypass -Command `"& '$BackendPython' 'infra/pacs/viewer_server.py' --port 8080 --orthanc http://localhost:8042`""

if ($NoViewer) {
    & npx concurrently -k -n backend,frontend -c blue,green $BackendCommand $FrontendCommand
} else {
    & npx concurrently -k -n viewer,backend,frontend -c magenta,blue,green $ViewerCommand $BackendCommand $FrontendCommand
}

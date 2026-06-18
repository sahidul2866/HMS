$ErrorActionPreference = "Stop"

$BackendDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvDir = Join-Path $BackendDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$RequirementsFile = Join-Path $BackendDir "requirements.txt"
$StampFile = Join-Path $VenvDir ".requirements.sha256"

function Get-SystemPython {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return $py.Source
    }

    throw "Python was not found. Install Python 3 and make sure 'python' or 'py' is on PATH."
}

Set-Location $BackendDir

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating backend virtualenv..."
    $SystemPython = Get-SystemPython
    if ((Split-Path $SystemPython -Leaf) -ieq "py.exe") {
        & $SystemPython -3 -m venv $VenvDir
    } else {
        & $SystemPython -m venv $VenvDir
    }
    & $VenvPython -m pip install --upgrade pip
}

$CurrentRequirementsHash = (Get-FileHash -Algorithm SHA256 $RequirementsFile).Hash.ToLowerInvariant()
$InstalledRequirementsHash = ""
if (Test-Path $StampFile) {
    $InstalledRequirementsHash = (Get-Content $StampFile -Raw).Trim().ToLowerInvariant()
}

if ($CurrentRequirementsHash -ne $InstalledRequirementsHash) {
    Write-Host "Installing backend requirements..."
    & $VenvPython -m pip install -r $RequirementsFile
    Set-Content -Path $StampFile -Value $CurrentRequirementsHash -NoNewline
} else {
    Write-Host "Backend requirements are up to date."
}

Write-Host "Running backend migrations and seed scripts..."
$env:PYTHONPATH = "."
& $VenvPython -m app.scripts.bootstrap_db
Write-Host "Backend bootstrap complete."

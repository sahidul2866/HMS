param(
    [int[]]$Ports = @(4200, 8000, 8080)
)

$ErrorActionPreference = "Continue"

Write-Host ("Cleaning up ports {0}..." -f ($Ports -join ", "))

foreach ($Port in $Ports) {
    $Connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    $ProcessIds = $Connections | Select-Object -ExpandProperty OwningProcess -Unique

    foreach ($ProcessId in $ProcessIds) {
        if (-not $ProcessId) {
            continue
        }

        try {
            Stop-Process -Id $ProcessId -Force -ErrorAction Stop
            Write-Host "Stopped process $ProcessId on port $Port"
        } catch {
            Write-Warning ("Could not stop process {0} on port {1}: {2}" -f $ProcessId, $Port, $_.Exception.Message)
        }
    }
}

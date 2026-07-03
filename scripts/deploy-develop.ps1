param(
    [switch]$Detach = $true
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env.develop")) {
    if (Test-Path ".env.develop.example") {
        Copy-Item ".env.develop.example" ".env.develop"
        Write-Host "Created .env.develop from .env.develop.example. Update secrets before first deploy."
    }
    else {
        throw ".env.develop not found and .env.develop.example is missing."
    }
}

$composeArgs = @("-f", "docker-compose.develop.yml", "up", "--build")
if ($Detach) {
    $composeArgs += "-d"
}

Write-Host "Running: docker compose $($composeArgs -join ' ')"
docker compose @composeArgs

 $hostPortLine = Get-Content .env.develop | Where-Object { $_ -match '^HOST_PORT=' } | Select-Object -First 1
 $hostPort = "8501"
 if ($hostPortLine) {
     $hostPort = $hostPortLine.Split('=')[1]
 }

Write-Host "Develop deploy completed."
Write-Host "App URL: http://localhost:$hostPort"
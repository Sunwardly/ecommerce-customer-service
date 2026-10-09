param([switch]$SkipBrowser)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
function Invoke-Check {
    param([string]$Directory, [string]$Program, [string[]]$Arguments)
    Push-Location $Directory
    try {
        & $Program @Arguments
        if ($LASTEXITCODE -ne 0) { throw "Check failed: $Program (exit $LASTEXITCODE)" }
    } finally { Pop-Location }
}
Invoke-Check $taskRoot 'uv' @('run', '--project', 'customer-service-backend', '--frozen', 'python', 'scripts/check_repository.py')
Invoke-Check "$taskRoot\customer-service-backend" 'uv' @('run', '--frozen', 'python', '-X', 'utf8', '-m', 'unittest', 'discover', '-s', 'tests', '-v')
Invoke-Check "$taskRoot\customer-service-backend" 'uv' @('run', '--frozen', 'python', '-X', 'utf8', 'check_flows.py')
Invoke-Check "$taskRoot\customer-service-backend" 'uv' @('run', '--frozen', 'python', '-X', 'utf8', 'check_steps.py')
Invoke-Check "$taskRoot\ecommerce-service-backend" 'uv' @('run', '--frozen', 'python', '-X', 'utf8', '-m', 'unittest', 'discover', '-s', 'tests', '-v')
Invoke-Check "$taskRoot\customer-service-frontend" 'npm.cmd' @('run', 'lint')
Invoke-Check "$taskRoot\customer-service-frontend" 'npm.cmd' @('audit', '--audit-level=high')
Invoke-Check "$taskRoot\customer-service-frontend" 'npm.cmd' @('run', 'build')
if (!$SkipBrowser) { Invoke-Check "$taskRoot\customer-service-frontend" 'npm.cmd' @('test') }
Invoke-Check "$taskRoot\customer-service-frontend\vue-demo" 'npm.cmd' @('audit', '--audit-level=high')
Invoke-Check "$taskRoot\customer-service-frontend\vue-demo" 'npm.cmd' @('run', 'build')
Write-Host 'All requested checks passed.'

param(
    [ValidateSet("ollama", "lmstudio")]
    [string]$Profile = "ollama",
    [string]$BindAddress = "0.0.0.0",
    [int]$Port = 8000,
    [switch]$Reload
)

$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env.$Profile"

if (-not (Test-Path $envFile)) {
    throw "Env profile not found: $envFile"
}

Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) {
        return
    }
    $parts = $line.Split("=", 2)
    if ($parts.Length -eq 2) {
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        [System.Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

Push-Location $root
try {
    $args = @("app.main:app", "--host", $BindAddress, "--port", $Port)
    if ($Reload) {
        $args += "--reload"
    }
    & uvicorn @args
} finally {
    Pop-Location
}

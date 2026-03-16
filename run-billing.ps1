# Requires -Version 5.1
param(
    [string]$Account          = "tottoco",
    [string]$Email            = "prac_desarrollo@totto.com",
    [int]   $Year             = 2025,
    [int]   $MonthStart       = 12,
    [int]   $MonthEnd         = 12,
    [bool]  $Headless         = $false,
    [bool]  $Debug            = $true,
    [bool]  $UseSavedSession  = $true,
    [bool]  $ForceRelogin     = $false,
    [string]$LoginUrl         = $null
)

# --- Forzar consola UTF-8 para evitar UnicodeEncodeError en Windows ---
try { chcp 65001 | Out-Null } catch {}
try {
    [Console]::OutputEncoding = [Text.UTF8Encoding]::UTF8
    $OutputEncoding = [Console]::OutputEncoding
} catch {}

# --- Paths ---
$RepoRoot   = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvScript = Join-Path $RepoRoot ".venv\Scripts\Activate.ps1"
$Downloads  = Join-Path $RepoRoot "billing_downloads"
$LogsDir    = Join-Path $Downloads "logs"
# Convención del proyecto: storage en billing_downloads
$Storage    = Join-Path $Downloads "vtex_session.json"

# --- Asegura carpetas ---
New-Item -ItemType Directory -Force -Path $Downloads | Out-Null
New-Item -ItemType Directory -Force -Path $LogsDir   | Out-Null

# --- Log ---
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$LogPath = Join-Path $LogsDir "run-$ts.log"

# --- Activa venv (si existe) ---
if (Test-Path $VenvScript) {
    Write-Host "Activando entorno virtual: $VenvScript"
    . $VenvScript
} else {
    Write-Warning "No se encontró .venv. Continuará con el intérprete por defecto."
}

# --- Construir argumentos para python -m vtex_invoices.main ---
# OJO: NO uses Resolve-Path con $Storage; puede no existir aún.
$args = @(
    "-m", "vtex_invoices.main",
    "--account", $Account,
    "--email",   $Email,
    "--year",    $Year,
    "--month-start", $MonthStart,
    "--month-end",   $MonthEnd,
    "--headless",    ($Headless.ToString().ToLower()),
    "--debug",       ($Debug.ToString().ToLower()),
    "--use-saved-session", ($UseSavedSession.ToString().ToLower()),
    "--force-relogin",     ($ForceRelogin.ToString().ToLower()),
    "--storage-state", $Storage
)
if ($LoginUrl) {
    $args += @("--login-url", $LoginUrl)
}

Write-Host "Iniciando extracción... (ver log: $LogPath)"

function Join-Args([string[]]$arr) {
    $escaped = $arr | ForEach-Object {
        if ($_ -match '\s') { '"' + $_.Replace('"','\"') + '"' } else { $_ }
    }
    return ($escaped -join ' ')
}
$argString = Join-Args $args

try {
    Push-Location $RepoRoot
    $cmd = 'python ' + $argString + ' 2>&1'
    Write-Host "CMD> $cmd"
    Invoke-Expression $cmd | Tee-Object -FilePath $LogPath -Append
    Pop-Location
}
catch {
    Write-Error "Fallo ejecutando vtex_invoices.main: $($_.Exception.Message)"
    Write-Host "Revisa el log: $LogPath"
    exit 1
}

Write-Host ""
Write-Host "✅ Proceso finalizado. Log: $LogPath"
Write-Host "Salidas esperadas:"
Write-Host "  JSON -> $Downloads\meses_invoices.json"
Write-Host "  CSV  -> $Downloads\facturacion_formateada.csv (delimitador ';' + 'sep=;')"
Write-Host "  XLSX -> $Downloads\facturacion_formateada.xlsx"
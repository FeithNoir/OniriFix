[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Push-Location $Root

try {
    $Python = Join-Path $Root ".venv\Scripts\python.exe"
    $PyInstaller = Join-Path $Root ".venv\Scripts\pyinstaller.exe"
    if (-not (Test-Path $Python)) {
        throw "No existe .venv. Crea el entorno con: python -m venv .venv"
    }

    Write-Host "Instalando dependencias de empaquetado..." -ForegroundColor Cyan
    & $Python -m pip install -e ".[build]"
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudieron instalar las dependencias de empaquetado."
    }

    Write-Host "Generando icono..." -ForegroundColor Cyan
    & $Python "scripts\generate_icon.py"
    if ($LASTEXITCODE -ne 0) {
        throw "Fallo al generar el icono."
    }

    Write-Host "Construyendo dist\OniriFix.exe..." -ForegroundColor Cyan
    & $PyInstaller --noconfirm --clean "OniriFix.spec"
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path (Join-Path $Root "dist\OniriFix.exe"))) {
        throw "PyInstaller no genero dist\OniriFix.exe."
    }

    if (-not $SkipTests) {
        Write-Host "Ejecutando pruebas..." -ForegroundColor Cyan
        & $Python -m pytest -q
        if ($LASTEXITCODE -ne 0) {
            throw "Las pruebas fallaron; no se genera el instalador."
        }
    }

    if (-not $SkipInstaller) {
        $Iscc = $null
        $Command = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($Command) {
            $Iscc = $Command.Source
        }
        if (-not $Iscc) {
            $Candidates = @(
                (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
                "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
                "C:\Program Files\Inno Setup 6\ISCC.exe"
            )
            $Iscc = $Candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
        }
        if (-not $Iscc) {
            throw "Inno Setup 6 no encontrado. Instalalo con: winget install --id JRSoftware.InnoSetup -e"
        }

        Write-Host "Construyendo instalador con Inno Setup..." -ForegroundColor Cyan
        & $Iscc "installer\OniriFix.iss"
        if ($LASTEXITCODE -ne 0) {
            throw "Inno Setup no pudo generar el instalador."
        }
    }

    Write-Host ""
    Write-Host "Artefactos generados:" -ForegroundColor Green
    Get-ChildItem (Join-Path $Root "dist") |
        Where-Object { $_.Name -like "OniriFix*" } |
        Select-Object Name, Length, LastWriteTime |
        Format-Table -AutoSize
}
finally {
    Pop-Location
}

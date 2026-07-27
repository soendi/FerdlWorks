param(
    [switch]$installer
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

# Version auslesen
$versionFile = Join-Path $RepoRoot "version.py"
$content = Get-Content $versionFile -Raw
if ($content -match 'VERSION\s*=\s*"([^"]+)"') {
    $version = $Matches[1]
} else {
    Write-Error "Version nicht gefunden"
    exit 1
}
Write-Host "Baue FerdlWorks v$version ..."

# Prüfe PyInstaller
$pyinstaller = Get-Command "pyinstaller" -ErrorAction SilentlyContinue
if (-not $pyinstaller) {
    Write-Host "Installiere PyInstaller..."
    pip install pyinstaller
}

# EXE bauen
$distDir = Join-Path $RepoRoot "dist"
if (Test-Path $distDir) {
    Remove-Item "$distDir\*" -Recurse -Force
}

pyinstaller --noconfirm --onefile --windowed `
    --name "FerdlWorks" `
    --icon "assets\ferdlworks.ico" `
    --add-data "assets\ferdlworks_theme.json;assets" `
    --add-data "assets\ferdlworks.ico;." `
    --hidden-import "customtkinter" `
    --hidden-import "PIL._tkinter_finder" `
    --hidden-import "win32print" `
    --hidden-import "winreg" `
    --hidden-import "packaging" `
    --hidden-import "packaging.version" `
    --collect-all "reportlab" `
    main.py

Write-Host "EXE gebaut: dist\FerdlWorks.exe"

if ($installer) {
    # Prüfe Inno Setup
    $iscc = "C:\Program Files (x86)\Inno Setup 7\ISCC.exe"
    if (-not (Test-Path $iscc)) {
        $iscc = "C:\Program Files\Inno Setup 7\ISCC.exe"
    }
    if (Test-Path $iscc) {
        Write-Host "Baue Installer mit Inno Setup..."
        & $iscc "installer\ferdlworks.iss"
        Write-Host "Installer erstellt: installer\FerdlWorks-Setup.exe"
    } else {
        Write-Warning "Inno Setup nicht gefunden. Installer nicht erstellt."
    }
}

Write-Host "Fertig."

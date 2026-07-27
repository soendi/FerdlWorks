param(
    [switch]$bump
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

# Version auslesen
$versionFile = Join-Path $RepoRoot "version.py"
$content = Get-Content $versionFile -Raw
if ($content -match 'VERSION\s*=\s*"([^"]+)"') {
    $currentVersion = $Matches[1]
} else {
    Write-Error "Version konnte nicht aus version.py gelesen werden"
    exit 1
}

Write-Host "Aktuelle Version: $currentVersion"

# Branch-Name ermitteln
$branch = git rev-parse --abbrev-ref HEAD
Write-Host "Branch: $branch"

# Status prüfen
$status = git status --porcelain
if (-not $status) {
    Write-Host "Keine Änderungen zum Committen."
} else {
    Write-Host "Änderungen gefunden, committe..."
    git add -A
    git commit -m "Update v$currentVersion"
}

# Pushen
Write-Host "Pushe zu Remote..."
git push origin $branch

# Nur bei -bump: Taggen und neuen Version erstellen
if ($bump) {
    # Versionsnummer erhöhen (Patch)
    $parts = $currentVersion -split '\.'
    $patch = [int]$parts[2] + 1
    $newVersion = "$($parts[0]).$($parts[1]).$patch"
    Write-Host "Erhöhe Version von $currentVersion auf $newVersion"

    # version.py aktualisieren
    $newContent = $content -replace 'VERSION\s*=\s*"[^"]+"', "VERSION = `"$newVersion`""
    Set-Content -Path $versionFile -Value $newContent -Encoding UTF8

    # Neuen Commit mit Versionssprung
    git add -A
    git commit -m "Bump Version v$newVersion"
    git push origin $branch

    # Tag erstellen
    git tag "v$newVersion"
    git push origin "v$newVersion"
    Write-Host "Tag v$newVersion erstellt und gepusht"

    # GitHub Release via gh CLI
    try {
        gh release create "v$newVersion" --title "v$newVersion" --notes "Version $newVersion"
        Write-Host "GitHub Release v$newVersion erstellt"
    } catch {
        Write-Warning "GitHub Release konnte nicht erstellt werden (gh CLI installiert?). Das Tag wurde trotzdem erstellt."
    }

    Write-Host "Neue Version: $newVersion"
} else {
    Write-Host "Kein Bump - nur gepusht. Verwende -bump für eine neue Version."
}

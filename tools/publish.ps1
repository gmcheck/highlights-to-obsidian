$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$versionFile = Join-Path $projectRoot "h2o\version.py"

if (-not (Test-Path $versionFile)) {
    Write-Error "version.py not found: $versionFile"
    exit 1
}

$versionContent = Get-Content $versionFile -Raw
if ($versionContent -match '_version\s*=\s*\((\d+),\s*(\d+),\s*(\d+)\)') {
    $version = "$($matches[1]).$($matches[2]).$($matches[3])"
} else {
    Write-Error "Could not parse version from version.py"
    exit 1
}

$zipDir = Join-Path $projectRoot "zip"
$zipName = "highlights-to-obsidian-$version.zip"
$zipPath = Join-Path $zipDir $zipName
$h2oDir = Join-Path $projectRoot "h2o"

if (-not (Test-Path $h2oDir)) {
    Write-Error "h2o directory not found: $h2oDir"
    exit 1
}

if (-not (Test-Path $zipDir)) {
    New-Item -ItemType Directory -Path $zipDir -Force | Out-Null
}

if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}

Compress-Archive -Path "$h2oDir\*" -DestinationPath $zipPath

Write-Host "Created $zipName (version $version) in zip/"

<#
.SYNOPSIS
    Highlights to Obsidian 插件发布打包脚本

.DESCRIPTION
    将 h2o 插件目录打包为 Calibre 可安装的 ZIP 插件包。
    版本号从 h2o\version.py 中自动读取，生成的 ZIP 文件名为
    highlights-to-obsidian-{version}.zip，存放于项目根目录的 zips\ 文件夹下。

.NOTES
    使用方式：
      powershell -ExecutionPolicy Bypass -File tools\publish.ps1

    输出示例：
      Created highlights-to-obsidian-1.5.0.zip (version 1.5.0) in zips/

    版本号格式：h2o\version.py 中定义 _version = (1, 5, 0)
    打包内容：h2o\ 目录下的所有文件（Calibre 插件标准结构）
    安装方式：Calibre → 首选项 → 插件 → 从文件加载插件 → 选择生成的 ZIP 文件
#>

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

$zipDir = Join-Path $projectRoot "zips"
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

Write-Host "Created $zipName (version $version) in zips/"

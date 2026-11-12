# Builds dist\SimpleConverter (PyInstaller) and installer\Output\SimpleConverter-Setup-<version>.exe (Inno Setup).
# Run from anywhere:  powershell -ExecutionPolicy Bypass -File installer\build.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { python -m venv .venv }
& $py -m pip install -q -r requirements.txt pyinstaller

# 1. icon
& $py -c "import sys; sys.path.insert(0, '.'); from simple_converter.registry import make_icon; make_icon()"

# 2. bundle the Python app
& $py -m PyInstaller launcher.pyw --noconfirm --clean --windowed --onedir `
    --name SimpleConverter `
    --icon assets\simple-converter.ico `
    --add-data "assets\simple-converter.ico;assets" `
    --collect-submodules simple_converter `
    --collect-all pillow_heif `
    --collect-data winotify `
    --exclude-module matplotlib --exclude-module IPython --exclude-module notebook
if ($LASTEXITCODE) { throw "PyInstaller failed" }

# 3. FFmpeg (essentials build) next to the exe
$ff = Join-Path $root "installer\ffmpeg"
if (-not (Test-Path "$ff\ffmpeg.exe")) {
    New-Item -ItemType Directory -Force $ff | Out-Null
    $zip = Join-Path $env:TEMP "ffmpeg-release-essentials.zip"
    Invoke-WebRequest "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" -OutFile $zip
    $x = Join-Path $env:TEMP "ffmpeg-extract"
    Remove-Item $x -Recurse -Force -ErrorAction SilentlyContinue
    Expand-Archive $zip $x
    $bin = Get-ChildItem $x -Recurse -Filter ffmpeg.exe | Select-Object -First 1
    Copy-Item (Join-Path $bin.DirectoryName "ffmpeg.exe"), (Join-Path $bin.DirectoryName "ffprobe.exe") $ff
    Copy-Item (Get-ChildItem $x -Recurse -Filter LICENSE* | Select-Object -First 1).FullName "$ff\LICENSE.txt"
}

# 4. installer
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 not found (winget install JRSoftware.InnoSetup)" }
& $iscc "installer\setup.iss"
if ($LASTEXITCODE) { throw "Inno Setup failed" }
Get-ChildItem installer\Output

# Ripper installer (Windows)
# Last modified: 2026-06-05--0149
#
# Installs Python deps, deploys the app to %LOCALAPPDATA%\Programs\Ripper,
# and creates a Desktop shortcut. Run from the project folder:
#   .\install.ps1
#
# Safe to re-run (idempotent): it upgrades deps and overwrites the deployed copy.

$ErrorActionPreference = 'Stop'
$src = $PSScriptRoot

Write-Host "Ripper installer" -ForegroundColor Cyan
Write-Host "================"

# --- 1. Python ---------------------------------------------------------------
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $py) {
    Write-Host "Python not found on PATH." -ForegroundColor Red
    Write-Host "Install Python 3.10+ (tick 'Add to PATH'): winget install Python.Python.3.12"
    exit 1
}
$pyDir  = Split-Path $py
$pythonw = Join-Path $pyDir 'pythonw.exe'
if (-not (Test-Path $pythonw)) { $pythonw = $py }   # fall back to console python
Write-Host "Python : $py"

# --- 2. ffmpeg ---------------------------------------------------------------
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-Host "ffmpeg : $((Get-Command ffmpeg).Source)"
} else {
    Write-Host "ffmpeg not found on PATH (needed to merge video+audio)." -ForegroundColor Yellow
    Write-Host "  Install with: winget install Gyan.FFmpeg"
}

# --- 3. Python packages ------------------------------------------------------
Write-Host "Installing/upgrading yt-dlp and gallery-dl..."
& $py -m pip install --upgrade --quiet yt-dlp gallery-dl
Write-Host ("  yt-dlp     " + (& $py -m yt_dlp --version))
Write-Host ("  gallery-dl " + (& $py -m gallery_dl --version))

# --- 4. Deploy app -----------------------------------------------------------
$appDir = Join-Path $env:LOCALAPPDATA 'Programs\Ripper'
New-Item -ItemType Directory -Force -Path $appDir | Out-Null
Copy-Item (Join-Path $src 'ripper.pyw') (Join-Path $appDir 'ripper.pyw') -Force
Copy-Item (Join-Path $src 'ripper.ico') (Join-Path $appDir 'ripper.ico') -Force
Write-Host "Deployed to: $appDir"

# --- 5. Desktop shortcut -----------------------------------------------------
$desktop = [Environment]::GetFolderPath('Desktop')
$lnk = Join-Path $desktop 'Ripper.lnk'
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($lnk)
$sc.TargetPath       = $pythonw
$sc.Arguments        = '"' + (Join-Path $appDir 'ripper.pyw') + '"'
$sc.WorkingDirectory = $appDir
$sc.IconLocation     = (Join-Path $appDir 'ripper.ico') + ',0'
$sc.Description       = 'One-click link ripper (yt-dlp + gallery-dl)'
$sc.Save()
Write-Host "Shortcut   : $lnk"

Write-Host ""
Write-Host "Done. Launch 'Ripper' from your Desktop." -ForegroundColor Green
Write-Host "First run: click 'Add' under Cookie files to load your cookies.txt (see README)."

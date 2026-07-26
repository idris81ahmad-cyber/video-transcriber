# Build a standalone Windows binary with PyInstaller.
# Usage: .\scripts\build_binary.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "-> Installing build dependencies..."
pip install -e ".[url]" pyinstaller

$entry = Join-Path $env:TEMP "vt_entry.py"
@"
from video_transcriber.cli import run
if __name__ == "__main__":
    run()
"@ | Set-Content -Path $entry -Encoding UTF8

Write-Host "-> Building binary..."
pyinstaller `
  --name video-transcriber `
  --onefile `
  --clean `
  --noconfirm `
  --console `
  --hidden-import video_transcriber `
  --collect-all faster_whisper `
  --collect-all ctranslate2 `
  $entry

Write-Host ""
Write-Host "Binary built: dist\video-transcriber.exe"
Write-Host "Test with: .\dist\video-transcriber.exe --version"
Write-Host ""
Write-Host "Note: the binary still requires ffmpeg on the host PATH."

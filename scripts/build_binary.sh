#!/usr/bin/env bash
# Build a standalone binary with PyInstaller.
# Usage: ./scripts/build_binary.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "→ Installing build dependencies…"
pip install -e ".[url]" pyinstaller

echo "→ Building binary…"
pyinstaller \
  --name video-transcriber \
  --onefile \
  --clean \
  --noconfirm \
  --console \
  --hidden-import video_transcriber \
  --hidden-import video_transcriber.cli \
  --hidden-import video_transcriber.core \
  --hidden-import video_transcriber.exporters \
  --hidden-import video_transcriber.utils \
  --hidden-import video_transcriber.config \
  --collect-all faster_whisper \
  --collect-all ctranslate2 \
  -c "from video_transcriber.cli import run; run()" \
  || true

# Prefer a clean entry-point module if the -c approach fails on some platforms
if [[ ! -f dist/video-transcriber ]]; then
  cat > /tmp/vt_entry.py << 'EOF'
from video_transcriber.cli import run
if __name__ == "__main__":
    run()
EOF
  pyinstaller \
    --name video-transcriber \
    --onefile \
    --clean \
    --noconfirm \
    --console \
    --hidden-import video_transcriber \
    --collect-all faster_whisper \
    --collect-all ctranslate2 \
    /tmp/vt_entry.py
fi

echo ""
echo "✓ Binary built: dist/video-transcriber"
echo "  Test with: ./dist/video-transcriber --version"
echo ""
echo "Note: the binary still requires ffmpeg on the host PATH."

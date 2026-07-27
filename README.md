# Video Transcriber

**Fast, accurate, fully local video & audio transcription** powered by [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper).

No cloud. No API keys. Works offline after the first model download.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Faster-Whisper](https://img.shields.io/badge/engine-Faster--Whisper-orange.svg)](https://github.com/SYSTRAN/faster-whisper)

---

## Highlights

- 🎬 Transcribe **video** or **audio** files
- 🎥 **YouTube & URL** support
- 👥 **Speaker diarization**
- 🌐 **Web UI** (Gradio)
- 🐳 **Docker** + standalone **binaries**
- ⚡ Concurrent batch processing (`--workers`)
- 📄 Config file for permanent defaults
- 📝 TXT / SRT / VTT / JSON / CSV export

---

## Installation

### From source

```bash
git clone https://github.com/idris81ahmad-cyber/video-transcriber.git
cd video-transcriber
python -m venv .venv && source .venv/bin/activate

pip install -e .
pip install -e ".[url]"              # YouTube
pip install -e ".[diarization]"      # Speakers
pip install -e ".[web]"              # Browser UI
```

Requires **FFmpeg** in PATH.

### Docker

```bash
# Build
docker compose build

# CLI — put media in ./data
mkdir -p data output
docker compose run --rm cli /data/interview.mp4 -f srt -o /output

# Web UI
docker compose up web
# open http://localhost:7860
```

Or plain Docker:

```bash
docker build -t video-transcriber .
docker run --rm -v "$PWD:/data" video-transcriber /data/video.mp4 -f srt
```

### Standalone binary

```bash
# Linux / macOS
chmod +x scripts/build_binary.sh
./scripts/build_binary.sh
./dist/video-transcriber --version

# Windows (PowerShell)
.\scripts\build_binary.ps1
.\dist\video-transcriber.exe --version
```

> The binary still needs **ffmpeg** on the host PATH.

---

## Quick Start

```bash
# CLI
video-transcriber interview.mp4
video-transcriber ./lectures -r -f srt --workers 2
video-transcriber "https://youtu.be/XXXX" --diarize -f srt

# Web UI
video-transcriber web
```

---

## Commands

| Command | Description |
|---------|-------------|
| *(default)* | Transcribe files / folders / URLs |
| `web` | Launch local Gradio browser UI |
| `doctor` | System check |
| `models` | Model recommendations |

### Local Gradio (fully offline with Faster-Whisper)

```bash
pip install 'video-transcriber[web]'
video-transcriber web
# open http://127.0.0.1:7860
```

```bash
video-transcriber web --port 8080
video-transcriber web --share          # public Gradio link
video-transcriber web --host 0.0.0.0   # listen on all interfaces
```

### Vercel web app (cloud Whisper)

The `web/` folder is a Next.js app deployed on Vercel.  
Local Faster-Whisper is too large / long-running for Vercel serverless, so the hosted UI uses **Groq or OpenAI Whisper**.

Live: https://video-transcriber-flame.vercel.app

```bash
cd web
npm install
cp .env.example .env.local
# set GROQ_API_KEY=...  (or OPENAI_API_KEY=...)
npm run dev
```

Deploy / update:

```bash
cd web
vercel --prod
# set GROQ_API_KEY or OPENAI_API_KEY in the Vercel project env vars
```

---

## Config File

```toml
# ~/.config/video-transcriber/config.toml
model = "medium"
device = "cuda"
format = "srt"
workers = 2
skip_existing = true
```

---

## License

MIT © 2026 idris81ahmad-cyber

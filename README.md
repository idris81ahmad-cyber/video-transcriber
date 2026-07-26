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
- ⚡ Concurrent batch processing (`--workers`)
- 📄 Config file for permanent defaults
- 📝 TXT / SRT / VTT / JSON export
- 🖥️ Beautiful terminal progress (overall + ETA)

---

## Installation

```bash
git clone https://github.com/idris81ahmad-cyber/video-transcriber.git
cd video-transcriber
python -m venv .venv && source .venv/bin/activate

pip install -e .
pip install -e ".[url]"             # YouTube
pip install -e ".[diarization]"     # Speakers
```

Requires **FFmpeg** in PATH.

---

## Quick Start

```bash
# Single file (default command)
video-transcriber interview.mp4

# Batch folder with 2 workers + SRT
video-transcriber ./lectures -r -f srt --workers 2

# YouTube + diarization
video-transcriber "https://youtu.be/XXXX" --diarize -f srt

# High quality
video-transcriber meeting.mp4 -m medium -d cuda -f srt,json
```

---

## Concurrent Batch Processing

```bash
# Process many files in parallel
video-transcriber ./recordings -r -f srt --workers 4 --skip-existing
```

- `--workers 1` (default) — sequential, safest for GPU
- `--workers N` — parallel workers with a shared model lock
- Progress bar shows overall completion + ETA

---

## Config File

```toml
# ~/.config/video-transcriber/config.toml
model = "medium"
device = "cuda"
format = "srt"
workers = 2
skip_existing = true
diarize = false
```

Then just run:

```bash
video-transcriber meeting.mp4
```

---

## Speaker Diarization

```bash
pip install 'video-transcriber[diarization]'
export HF_TOKEN=hf_xxxxxxxx   # after accepting model conditions
video-transcriber meeting.mp4 --diarize -f srt
```

---

## Commands

| Command | Description |
|---------|-------------|
| *(default)* | Transcribe files / folders / URLs |
| `doctor` | System check |
| `models` | Model recommendations |
| `--version` | Version |

---

## License

MIT © 2026 idris81ahmad-cyber

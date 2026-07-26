# Video Transcriber

**Fast, accurate, fully local video & audio transcription** powered by [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper).

No cloud. No API keys. Works offline after the first model download.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Faster-Whisper](https://img.shields.io/badge/engine-Faster--Whisper-orange.svg)](https://github.com/SYSTRAN/faster-whisper)

---

## Highlights

- 🎬 Transcribe **video** (MP4, MOV, MKV, WebM…) or **audio** files
- 🎥 **YouTube & URL support** (via yt-dlp)
- 👥 **Speaker diarization** (who spoke when)
- ⚡ Extremely fast (CTranslate2 + optional GPU)
- 📄 **Config file** support for permanent defaults
- 📝 Export to **TXT / SRT / VTT / JSON**
- 📁 Batch folders + skip already done files
- 🖥️ Beautiful terminal UI (Typer + Rich)

---

## Installation

```bash
git clone https://github.com/idris81ahmad-cyber/video-transcriber.git
cd video-transcriber

python -m venv .venv
source .venv/bin/activate

pip install -e .
pip install -e ".[url]"            # YouTube support
pip install -e ".[diarization]"    # Speaker labels
```

Requires **FFmpeg** in your PATH.

---

## Quick Start

```bash
# Simplest possible usage (default command)
video-transcriber interview.mp4

# Explicit command still works
video-transcriber transcribe interview.mp4

# With speaker diarization + subtitles
video-transcriber interview.mp4 --diarize -f srt

# YouTube
video-transcriber "https://youtu.be/XXXX" -m medium -f srt

# Whole folder
video-transcriber ./recordings -r -f srt --skip-existing
```

---

## Config File

Create a config file so you don't have to repeat flags every time.

**Locations** (first found wins):

1. `./video-transcriber.toml` (project local)
2. `~/.config/video-transcriber/config.toml`
3. `~/.video-transcriber.toml`

**Example** `~/.config/video-transcriber/config.toml`:

```toml
model = "medium"
device = "cuda"
format = "srt"
diarize = true
skip_existing = true
language = "en"
```

After that you can simply run:

```bash
video-transcriber meeting.mp4
```

and it will use `medium` + CUDA + SRT + diarization automatically.

CLI flags always override the config file.

---

## Speaker Diarization

```bash
pip install 'video-transcriber[diarization]'

# Accept model conditions + set token
# https://huggingface.co/pyannote/speaker-diarization-3.1
export HF_TOKEN=hf_xxxxxxxx

video-transcriber meeting.mp4 --diarize -f srt
```

---

## YouTube / URL Support

```bash
pip install 'video-transcriber[url]'
video-transcriber "https://www.youtube.com/watch?v=XXXX" -f srt
```

---

## Commands

| Command | Description |
|---------|-------------|
| *(default)* / `transcribe` | Transcribe files / folders / URLs |
| `doctor` | Check system dependencies |
| `models` | Show model recommendations |
| `--version` | Show version |

---

## License

MIT © 2026 idris81ahmad-cyber

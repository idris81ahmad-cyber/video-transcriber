# Video Transcriber

**Fast, accurate, fully local video & audio transcription** powered by [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper).

No cloud. No API keys. Works offline after the first model download.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Faster-Whisper](https://img.shields.io/badge/engine-Faster--Whisper-orange.svg)](https://github.com/SYSTRAN/faster-whisper)

---

## Highlights

- 🎬 Transcribe **video** (MP4, MOV, MKV, WebM…) or **audio** files
- 🎥 **YouTube & URL support** (via yt-dlp) — just paste a link
- ⚡ Extremely fast thanks to CTranslate2 + optional GPU
- 🌐 Auto language detection + 99 languages
- ⏱️ Segment or **word-level** timestamps
- 📝 Export to **TXT / SRT / VTT / JSON** (multiple at once)
- 📁 Batch folders (recursive) + skip already transcribed files
- 🖥️ Beautiful terminal UI with `rich` + `typer`
- 🔍 Built-in `doctor` and `models` commands

---

## Installation

### Prerequisites

- Python 3.9+
- [FFmpeg](https://ffmpeg.org/) in your PATH

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt update && sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html and add to PATH
```

### Install from source (recommended while developing)

```bash
git clone https://github.com/idris81ahmad-cyber/video-transcriber.git
cd video-transcriber

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Core only
pip install -e .

# With YouTube / URL support
pip install -e ".[url]"
```

After installation you can use either:

```bash
video-transcriber --help
# or
transcribe --help
```

> Once published to PyPI you will also be able to install with:
> `pip install video-transcriber` or `pip install "video-transcriber[url]"`

---

## Quick Start

```bash
# Local file
video-transcriber transcribe interview.mp4

# YouTube / any supported URL
video-transcriber transcribe "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -f srt

# High quality subtitles
video-transcriber transcribe lecture.mp4 -m medium -f srt

# Multiple formats at once
video-transcriber transcribe meeting.mp4 -f srt,vtt,json

# Whole folder, recursive, skip already done
video-transcriber transcribe ./recordings -r -f srt --skip-existing

# Force language + GPU
video-transcriber transcribe video.mp4 -l en -d cuda -m large-v3

# Word-level timestamps
video-transcriber transcribe podcast.mp3 --word-timestamps -f json
```

---

## YouTube & URL Support

Any URL that **yt-dlp** can handle works (YouTube, Vimeo, Twitter/X, many others).

```bash
# Install the optional extra once
pip install 'video-transcriber[url]'

# Then just pass the link
video-transcriber transcribe "https://youtu.be/XXXX" -m medium -f srt,vtt
```

- The tool downloads **audio only** (much faster & smaller)
- Temporary files are cleaned up automatically
- Output is saved in the current directory using a sanitized title

---

## Commands

| Command | Description |
|---------|-------------|
| `transcribe` | Main transcription command |
| `doctor`    | Check ffmpeg, yt-dlp, CUDA, package health |
| `models`    | Show model size / speed / accuracy table |
| `--version` | Show package version |

---

## Recommended Models

| Model      | Relative Speed | Accuracy   | VRAM (approx) | Best for                  |
|------------|----------------|------------|---------------|---------------------------|
| `tiny`     | Very Fast      | Low        | ~1 GB         | Quick drafts / testing    |
| `base`     | Fast           | Decent     | ~1 GB         | Everyday short clips      |
| `small`    | Good           | Good       | ~2 GB         | **Balanced default**      |
| `medium`   | Medium         | High       | ~5 GB         | High quality work         |
| `large-v3` | Slower         | Best       | ~10 GB        | Maximum accuracy          |

> On CPU the tool automatically uses `int8` quantization for speed.  
> On CUDA it prefers `float16`.

---

## System Check

```bash
video-transcriber doctor
```

---

## Publishing to PyPI (for maintainers)

The project is already prepared for PyPI. To publish:

```bash
# 1. Install build tools
pip install build twine

# 2. Build the package
python -m build

# 3. Check the distribution
twine check dist/*

# 4. Upload (you need a PyPI account + API token)
twine upload dist/*
```

**Recommended workflow:**

1. Create an account on [pypi.org](https://pypi.org)
2. Generate an API token under Account settings → API tokens
3. Use the token as password when `twine` asks for credentials (username = `__token__`)

After the first successful upload, users will be able to install with:

```bash
pip install video-transcriber
pip install "video-transcriber[url]"   # with YouTube support
```

---

## Project Structure

```
src/video_transcriber/
├── cli.py          # Typer + Rich CLI
├── core.py         # Transcription engine
├── exporters.py    # TXT / SRT / VTT / JSON writers
├── utils.py        # ffmpeg, yt-dlp, file discovery, timestamps
├── __init__.py
├── __main__.py
└── py.typed
```

---

## License

MIT © 2026 idris81ahmad-cyber

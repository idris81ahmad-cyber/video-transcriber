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
- 👥 **Speaker diarization** (who spoke when) via pyannote
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

### Install from source

```bash
git clone https://github.com/idris81ahmad-cyber/video-transcriber.git
cd video-transcriber

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Core only
pip install -e .

# With YouTube / URL support
pip install -e ".[url]"

# With speaker diarization
pip install -e ".[diarization]"

# Everything
pip install -e ".[url,diarization]"
```

---

## Quick Start

```bash
# Local file
video-transcriber transcribe interview.mp4

# With speaker labels
video-transcriber transcribe interview.mp4 --diarize -f srt

# YouTube
video-transcriber transcribe "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -f srt

# High quality + diarization
video-transcriber transcribe meeting.mp4 -m medium --diarize -f srt,json
```

---

## Speaker Diarization

Identify **who spoke when**.

```bash
pip install 'video-transcriber[diarization]'
```

You also need a Hugging Face token:

1. Accept the model conditions:  
   https://huggingface.co/pyannote/speaker-diarization-3.1
2. Create a token at https://huggingface.co/settings/tokens
3. Export it:

```bash
export HF_TOKEN=hf_xxxxxxxxxxxxxxxx
```

Then run:

```bash
video-transcriber transcribe meeting.mp4 --diarize -f srt
```

Output example (SRT):

```
1
00:00:01,200 --> 00:00:04,800
[SPEAKER_00] Welcome everyone to today's meeting.

2
00:00:05,100 --> 00:00:08,400
[SPEAKER_01] Thanks. Let's start with the agenda.
```

---

## YouTube & URL Support

```bash
pip install 'video-transcriber[url]'

video-transcriber transcribe "https://youtu.be/XXXX" -m medium -f srt,vtt
```

---

## Commands

| Command | Description |
|---------|-------------|
| `transcribe` | Main transcription command |
| `doctor`    | Check ffmpeg, yt-dlp, diarization, CUDA |
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

---

## System Check

```bash
video-transcriber doctor
```

---

## License

MIT © 2026 idris81ahmad-cyber

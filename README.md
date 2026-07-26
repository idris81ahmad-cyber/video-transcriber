# Video Transcriber

Fast, accurate, local video & audio transcription powered by **Faster-Whisper**.

No cloud required. Works fully offline after the model is downloaded.

## Features

- 🎬 Transcribe video (MP4, MOV, MKV, WebM…) or audio files
- ⚡ Uses [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) — much faster & lighter than original Whisper
- 🌐 Auto language detection + 99 languages supported
- ⏱️ Accurate word-level or segment-level timestamps
- 📝 Export to **TXT**, **SRT**, **VTT**, or **JSON**
- 🖥️ Runs on CPU or CUDA (GPU)
- 📁 Simple CLI — just point it at a file

## Requirements

- Python 3.9+
- [FFmpeg](https://ffmpeg.org/) installed and available in PATH
- (Optional) CUDA for GPU acceleration

## Installation

```bash
git clone https://github.com/idris81ahmad-cyber/video-transcriber.git
cd video-transcriber

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## Usage

### Basic

```bash
python transcribe.py path/to/video.mp4
```

### Common options

```bash
# Choose model size (tiny / base / small / medium / large-v3)
python transcribe.py video.mp4 --model medium

# Force language
python transcribe.py video.mp4 --language en

# Output formats
python transcribe.py video.mp4 --format srt
python transcribe.py video.mp4 --format vtt
python transcribe.py video.mp4 --format json

# Use GPU
python transcribe.py video.mp4 --device cuda

# Custom output path
python transcribe.py video.mp4 -o transcript.srt

# Word-level timestamps
python transcribe.py video.mp4 --word-timestamps
```

### Full help

```bash
python transcribe.py --help
```

## Recommended Models

| Model       | VRAM (approx) | Speed     | Accuracy     | Recommendation          |
|-------------|---------------|-----------|--------------|-------------------------|
| `tiny`      | ~1 GB         | Very fast | Low          | Quick drafts            |
| `base`      | ~1 GB         | Fast      | Decent       | Everyday use            |
| `small`     | ~2 GB         | Good      | Good         | Balanced (default)      |
| `medium`    | ~5 GB         | Medium    | High         | High quality            |
| `large-v3`  | ~10 GB        | Slower    | Best         | Maximum accuracy        |

## Notes

- First run downloads the model automatically (~ hundreds of MB to a few GB).
- Models are cached in `~/.cache/huggingface/` by default.
- For best results on long videos, use `--model medium` or `large-v3` + GPU.

## License

MIT

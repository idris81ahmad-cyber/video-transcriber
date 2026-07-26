"""Utility helpers for video-transcriber."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional

from rich.console import Console

console = Console()

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".flv", ".m4v", ".wmv", ".mpeg", ".mpg"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma", ".opus"}
MEDIA_EXTS = VIDEO_EXTS | AUDIO_EXTS


def check_ffmpeg() -> bool:
    """Return True if ffmpeg is available in PATH."""
    return shutil.which("ffmpeg") is not None


def extract_audio(video_path: Path, output_path: Optional[Path] = None) -> Path:
    """
    Extract mono 16kHz PCM WAV from a video file using ffmpeg.
    Returns the path to the extracted audio.
    """
    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        output_path = Path(tmp.name)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_path),
    ]

    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg not found. Please install ffmpeg and ensure it is in your PATH.\n"
            "  macOS: brew install ffmpeg\n"
            "  Ubuntu: sudo apt install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html"
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg failed to extract audio:\n{e.stderr}") from e

    return output_path


def format_timestamp(seconds: float, *, always_include_hours: bool = True, decimal_marker: str = ",") -> str:
    """Format seconds into HH:MM:SS,mmm or MM:SS,mmm."""
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = milliseconds // 3_600_000
    milliseconds -= hours * 3_600_000

    minutes = milliseconds // 60_000
    milliseconds -= minutes * 60_000

    secs = milliseconds // 1_000
    milliseconds -= secs * 1_000

    if always_include_hours or hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}{decimal_marker}{milliseconds:03d}"
    return f"{minutes:02d}:{secs:02d}{decimal_marker}{milliseconds:03d}"


def discover_media(path: Path, recursive: bool = False) -> List[Path]:
    """Find all supported media files under a path."""
    if path.is_file():
        if path.suffix.lower() in MEDIA_EXTS:
            return [path]
        return []

    pattern = "**/*" if recursive else "*"
    files = []
    for p in path.glob(pattern):
        if p.is_file() and p.suffix.lower() in MEDIA_EXTS:
            files.append(p)
    return sorted(files)


def is_url(value: str) -> bool:
    return value.startswith(("http://", "https://", "www."))

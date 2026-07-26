"""Utility helpers for video-transcriber."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console

console = Console()

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".flv", ".m4v", ".wmv", ".mpeg", ".mpg"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma", ".opus"}
MEDIA_EXTS = VIDEO_EXTS | AUDIO_EXTS


def check_ffmpeg() -> bool:
    """Return True if ffmpeg is available in PATH."""
    return shutil.which("ffmpeg") is not None


def check_ytdlp() -> bool:
    """Return True if yt-dlp is importable."""
    try:
        import yt_dlp  # noqa: F401
        return True
    except ImportError:
        return False


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


def download_from_url(
    url: str,
    output_dir: Optional[Path] = None,
    *,
    audio_only: bool = True,
) -> Tuple[Path, str]:
    """
    Download media from a URL (YouTube, Vimeo, etc.) using yt-dlp.

    Returns:
        (path_to_downloaded_file, suggested_title)
    """
    if not check_ytdlp():
        raise RuntimeError(
            "yt-dlp is required for URL support.\n"
            "Install it with:\n"
            "  pip install 'video-transcriber[url]'\n"
            "or\n"
            "  pip install yt-dlp"
        )

    import yt_dlp

    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="video-transcriber-"))
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Prefer best audio for transcription efficiency
    if audio_only:
        format_selector = "bestaudio/best"
        outtmpl = str(output_dir / "%(title).200B [%(id)s].%(ext)s")
    else:
        format_selector = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
        outtmpl = str(output_dir / "%(title).200B [%(id)s].%(ext)s")

    ydl_opts = {
        "format": format_selector,
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,          # single video only
        "extract_flat": False,
        # Post-process to a consistent format when possible
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }
        ] if audio_only else [],
    }

    # If we only want audio we force wav for Whisper friendliness
    if audio_only:
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }
        ]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise RuntimeError("yt-dlp could not extract video information")

            title = info.get("title") or info.get("id") or "downloaded"
            # After post-processing the file extension becomes .wav
            if audio_only:
                # Find the resulting .wav file
                downloaded = list(output_dir.glob("*.wav"))
                if not downloaded:
                    # Fallback: look for any media file
                    downloaded = list(output_dir.glob("*.*"))
                if not downloaded:
                    raise RuntimeError("Download succeeded but no file was found")
                path = downloaded[0]
            else:
                # Best effort to locate the file
                filename = ydl.prepare_filename(info)
                path = Path(filename)
                if not path.exists():
                    # Try common extensions
                    for ext in (".mp4", ".webm", ".mkv", ".m4a", ".mp3"):
                        candidate = path.with_suffix(ext)
                        if candidate.exists():
                            path = candidate
                            break

            return path.resolve(), title

    except Exception as e:
        raise RuntimeError(f"Failed to download from URL:\n{e}") from e


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

"""Configuration loading for video-transcriber."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# tomllib is stdlib in 3.11+, fall back to tomli for older Python
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore
    except ModuleNotFoundError:
        tomllib = None  # type: ignore


DEFAULT_CONFIG: Dict[str, Any] = {
    "model": "small",
    "device": "cpu",
    "compute_type": None,
    "language": None,
    "format": "txt",
    "word_timestamps": False,
    "beam_size": 5,
    "vad": True,
    "diarize": False,
    "recursive": False,
    "skip_existing": False,
    "quiet": False,
    "output": None,
}


def _config_paths() -> list[Path]:
    """Return config file locations in priority order (highest first)."""
    paths = [
        Path.cwd() / "video-transcriber.toml",
        Path.cwd() / ".video-transcriber.toml",
    ]

    # XDG config home
    xdg = Path.home() / ".config" / "video-transcriber" / "config.toml"
    paths.append(xdg)

    # Legacy / simple home location
    paths.append(Path.home() / ".video-transcriber.toml")

    return paths


def load_config() -> Dict[str, Any]:
    """
    Load configuration from the first existing config file.

    Returns a dict with defaults filled in for missing keys.
    """
    cfg = dict(DEFAULT_CONFIG)

    if tomllib is None:
        return cfg

    for path in _config_paths():
        if path.is_file():
            try:
                with path.open("rb") as f:
                    data = tomllib.load(f)
                # Support both flat and [defaults] section
                if "defaults" in data and isinstance(data["defaults"], dict):
                    data = data["defaults"]
                for key, value in data.items():
                    if key in DEFAULT_CONFIG:
                        cfg[key] = value
                break
            except Exception:
                # Silently ignore broken config files
                continue

    return cfg


def config_help_text() -> str:
    """Return a short help string about config files."""
    locations = "\n".join(f"  • {p}" for p in _config_paths())
    return (
        "Config file locations (first found wins):\n"
        f"{locations}\n\n"
        "Example video-transcriber.toml:\n\n"
        "  model = \"medium\"\n"
        "  device = \"cuda\"\n"
        "  format = \"srt\"\n"
        "  diarize = true\n"
        "  skip_existing = true\n"
    )

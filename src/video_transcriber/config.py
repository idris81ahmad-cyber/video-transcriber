"""Configuration loading for video-transcriber."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

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
    "workers": 1,
}


def _config_paths() -> list[Path]:
    return [
        Path.cwd() / "video-transcriber.toml",
        Path.cwd() / ".video-transcriber.toml",
        Path.home() / ".config" / "video-transcriber" / "config.toml",
        Path.home() / ".video-transcriber.toml",
    ]


def load_config() -> Dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    if tomllib is None:
        return cfg

    for path in _config_paths():
        if path.is_file():
            try:
                with path.open("rb") as f:
                    data = tomllib.load(f)
                if "defaults" in data and isinstance(data["defaults"], dict):
                    data = data["defaults"]
                for key, value in data.items():
                    if key in DEFAULT_CONFIG:
                        cfg[key] = value
                break
            except Exception:
                continue
    return cfg

"""Output format writers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, List, Optional

from video_transcriber.utils import format_timestamp


def _speaker_prefix(segment: Any) -> str:
    speaker = getattr(segment, "speaker", None)
    if speaker:
        return f"[{speaker}] "
    return ""


def write_txt(segments: Iterable[Any], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for segment in segments:
            text = segment.text.strip()
            if text:
                f.write(_speaker_prefix(segment) + text + "\n")


def write_srt(segments: Iterable[Any], path: Path, *, word_level: bool = False) -> None:
    with path.open("w", encoding="utf-8") as f:
        index = 1
        for segment in segments:
            if word_level and hasattr(segment, "words") and segment.words:
                for word in segment.words:
                    if word.start is None or word.end is None:
                        continue
                    start = format_timestamp(word.start, decimal_marker=",")
                    end = format_timestamp(word.end, decimal_marker=",")
                    f.write(f"{index}\n")
                    f.write(f"{start} --> {end}\n")
                    f.write(f"{word.word.strip()}\n\n")
                    index += 1
            else:
                start = format_timestamp(segment.start, decimal_marker=",")
                end = format_timestamp(segment.end, decimal_marker=",")
                text = segment.text.strip()
                if not text:
                    continue
                f.write(f"{index}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{_speaker_prefix(segment)}{text}\n\n")
                index += 1


def write_vtt(segments: Iterable[Any], path: Path, *, word_level: bool = False) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for segment in segments:
            if word_level and hasattr(segment, "words") and segment.words:
                for word in segment.words:
                    if word.start is None or word.end is None:
                        continue
                    start = format_timestamp(word.start, decimal_marker=".")
                    end = format_timestamp(word.end, decimal_marker=".")
                    f.write(f"{start} --> {end}\n")
                    f.write(f"{word.word.strip()}\n\n")
            else:
                start = format_timestamp(segment.start, decimal_marker=".")
                end = format_timestamp(segment.end, decimal_marker=".")
                text = segment.text.strip()
                if not text:
                    continue
                f.write(f"{start} --> {end}\n")
                f.write(f"{_speaker_prefix(segment)}{text}\n\n")


def write_json(
    segments: Iterable[Any],
    path: Path,
    *,
    language: Optional[str] = None,
    language_probability: Optional[float] = None,
    duration: Optional[float] = None,
    word_level: bool = False,
) -> None:
    data: dict[str, Any] = {
        "language": language,
        "language_probability": language_probability,
        "duration": duration,
        "segments": [],
    }

    for i, segment in enumerate(segments):
        seg: dict[str, Any] = {
            "id": i,
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
        }
        speaker = getattr(segment, "speaker", None)
        if speaker:
            seg["speaker"] = speaker

        if word_level and hasattr(segment, "words") and segment.words:
            seg["words"] = [
                {
                    "word": w.word,
                    "start": w.start,
                    "end": w.end,
                    "probability": getattr(w, "probability", None),
                }
                for w in segment.words
                if w.start is not None
            ]
        data["segments"].append(seg)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def export(
    segments: List[Any],
    path: Path,
    fmt: str,
    *,
    language: Optional[str] = None,
    language_probability: Optional[float] = None,
    duration: Optional[float] = None,
    word_level: bool = False,
) -> None:
    """Dispatch to the correct writer."""
    fmt = fmt.lower()
    if fmt == "txt":
        write_txt(segments, path)
    elif fmt == "srt":
        write_srt(segments, path, word_level=word_level)
    elif fmt == "vtt":
        write_vtt(segments, path, word_level=word_level)
    elif fmt == "json":
        write_json(
            segments,
            path,
            language=language,
            language_probability=language_probability,
            duration=duration,
            word_level=word_level,
        )
    else:
        raise ValueError(f"Unsupported format: {fmt}")

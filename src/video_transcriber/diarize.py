"""Speaker diarization helpers (optional dependency)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

from rich.console import Console

console = Console()


@dataclass
class SpeakerSegment:
    start: float
    end: float
    speaker: str


def check_diarization_available() -> bool:
    try:
        import pyannote.audio  # noqa: F401

        return True
    except ImportError:
        return False


def load_diarization_pipeline(device: str = "cpu"):
    """
    Load the pyannote speaker-diarization pipeline.

    Requires:
      - pip install 'video-transcriber[diarization]'
      - Hugging Face token with access to pyannote models
        (set HF_TOKEN environment variable)
    """
    try:
        from pyannote.audio import Pipeline
        import torch
    except ImportError as e:
        raise RuntimeError(
            "Speaker diarization requires the optional extra.\n"
            "Install with:\n"
            "  pip install 'video-transcriber[diarization]'\n\n"
            "You also need a Hugging Face token with access to:\n"
            "  https://huggingface.co/pyannote/speaker-diarization-3.1\n"
            "Set it as: export HF_TOKEN=hf_..."
        ) from e

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        raise RuntimeError(
            "HF_TOKEN is not set.\n"
            "1. Accept model conditions: https://huggingface.co/pyannote/speaker-diarization-3.1\n"
            "2. Create a token: https://huggingface.co/settings/tokens\n"
            "3. export HF_TOKEN=hf_..."
        )

    console.print("[bold cyan]Loading speaker diarization pipeline…[/]")

    # Prefer modern `token=` API; fall back for older pyannote versions
    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            token=token,
        )
    except TypeError:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=token,
        )

    if device == "cuda" and torch.cuda.is_available():
        pipeline.to(torch.device("cuda"))
    else:
        pipeline.to(torch.device("cpu"))

    return pipeline


def run_diarization(pipeline, audio_path: Path) -> List[SpeakerSegment]:
    """Run diarization and return a list of speaker turns."""
    console.print("[dim]Running speaker diarization…[/]")

    diarization = pipeline(str(audio_path))

    segments: List[SpeakerSegment] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append(
            SpeakerSegment(
                start=turn.start,
                end=turn.end,
                speaker=str(speaker),
            )
        )

    segments.sort(key=lambda s: s.start)
    return segments


def assign_speakers_to_transcript(
    transcript_segments: List[Any],
    speaker_segments: List[SpeakerSegment],
) -> List[Any]:
    """
    Assign the most overlapping speaker to each transcript segment.

    Mutates the segments in-place by adding a `.speaker` attribute.
    """
    if not speaker_segments:
        for seg in transcript_segments:
            seg.speaker = "SPEAKER_00"
        return transcript_segments

    for seg in transcript_segments:
        best_speaker = "SPEAKER_00"
        best_overlap = 0.0

        for sp in speaker_segments:
            overlap_start = max(seg.start, sp.start)
            overlap_end = min(seg.end, sp.end)
            overlap = max(0.0, overlap_end - overlap_start)

            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = sp.speaker

        seg.speaker = best_speaker

    return transcript_segments

"""Core transcription logic using Faster-Whisper."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

from faster_whisper import WhisperModel
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from video_transcriber.exporters import export
from video_transcriber.utils import VIDEO_EXTS, extract_audio

console = Console()


@dataclass
class TranscriptionResult:
    segments: List[Any]
    language: str
    language_probability: float
    duration: float


def load_model(
    model_size: str = "small",
    device: str = "cpu",
    compute_type: Optional[str] = None,
    download_root: Optional[str] = None,
    *,
    quiet: bool = False,
) -> WhisperModel:
    """Load a Faster-Whisper model with sensible defaults."""
    if compute_type is None:
        compute_type = "float16" if device == "cuda" else "int8"

    if not quiet:
        console.print(
            f"[bold cyan]Loading model[/] [yellow]{model_size}[/] "
            f"on [green]{device}[/] ([dim]{compute_type}[/])…"
        )

    return WhisperModel(
        model_size,
        device=device,
        compute_type=compute_type,
        download_root=download_root,
    )


def transcribe_file(
    model: WhisperModel,
    media_path: Path,
    *,
    language: Optional[str] = None,
    beam_size: int = 5,
    word_timestamps: bool = False,
    vad_filter: bool = True,
    vad_parameters: Optional[dict] = None,
    diarize: bool = False,
    diarization_pipeline: Any = None,
    device: str = "cpu",
    quiet: bool = False,
) -> TranscriptionResult:
    """
    Transcribe a single media file.
    Automatically extracts audio if the input is a video.
    Optionally runs speaker diarization.
    """
    media_path = media_path.resolve()
    is_video = media_path.suffix.lower() in VIDEO_EXTS

    temp_audio: Optional[Path] = None
    audio_path = media_path

    try:
        if is_video:
            if not quiet:
                console.print(f"[dim]Extracting audio from[/] {media_path.name}…")
            temp_audio = extract_audio(media_path)
            audio_path = temp_audio

        if not quiet:
            console.print(f"[bold]Transcribing[/] {media_path.name}…")

        segments_gen, info = model.transcribe(
            str(audio_path),
            language=language,
            beam_size=beam_size,
            word_timestamps=word_timestamps,
            vad_filter=vad_filter,
            vad_parameters=vad_parameters or {},
        )

        segments: List[Any] = []
        if quiet:
            # Fast path — no progress UI
            for segment in segments_gen:
                segments.append(segment)
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task("Processing segments…", total=None)
                for segment in segments_gen:
                    segments.append(segment)
                    progress.update(task, advance=1)

        if diarize:
            from video_transcriber.diarize import (
                assign_speakers_to_transcript,
                load_diarization_pipeline,
                run_diarization,
            )

            pipeline = diarization_pipeline or load_diarization_pipeline(device=device)
            speaker_turns = run_diarization(pipeline, audio_path)
            segments = assign_speakers_to_transcript(segments, speaker_turns)

            if not quiet:
                n_speakers = len({getattr(s, "speaker", "?") for s in segments})
                console.print(f"[green]✓[/] Detected [bold]{n_speakers}[/] speaker(s)")

        return TranscriptionResult(
            segments=segments,
            language=info.language,
            language_probability=info.language_probability,
            duration=info.duration,
        )
    finally:
        if temp_audio is not None and temp_audio.exists():
            try:
                os.unlink(temp_audio)
            except OSError:
                pass


def save_result(
    result: TranscriptionResult,
    output_path: Path,
    formats: List[str],
    *,
    word_level: bool = False,
) -> List[Path]:
    """Write one or more output formats. Returns list of written files."""
    written: List[Path] = []

    for fmt in formats:
        if len(formats) == 1:
            path = output_path
            if path.suffix.lower() != f".{fmt}":
                path = output_path.with_suffix(f".{fmt}")
        else:
            path = output_path.with_suffix(f".{fmt}")

        export(
            result.segments,
            path,
            fmt,
            language=result.language,
            language_probability=result.language_probability,
            duration=result.duration,
            word_level=word_level,
        )
        written.append(path)

    return written

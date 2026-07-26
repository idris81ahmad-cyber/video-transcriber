"""Command-line interface for Video Transcriber."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from video_transcriber import __version__
from video_transcriber.core import load_model, save_result, transcribe_file
from video_transcriber.utils import (
    MEDIA_EXTS,
    check_ffmpeg,
    discover_media,
    is_url,
)

app = typer.Typer(
    name="video-transcriber",
    help="Fast, accurate, local video & audio transcription powered by Faster-Whisper.",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"[bold cyan]video-transcriber[/] v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Video Transcriber — local speech-to-text for video & audio."""
    pass


@app.command("transcribe")
def transcribe(
    inputs: List[str] = typer.Argument(
        ...,
        help="One or more media files, folders, or YouTube/URL links.",
    ),
    model: str = typer.Option(
        "small",
        "--model",
        "-m",
        help="Whisper model size: tiny, base, small, medium, large-v2, large-v3",
        rich_help_panel="Model",
    ),
    device: str = typer.Option(
        "cpu",
        "--device",
        "-d",
        help="Device to run on: cpu or cuda",
        rich_help_panel="Model",
    ),
    compute_type: Optional[str] = typer.Option(
        None,
        "--compute-type",
        help="Quantization (int8, float16, float32…). Auto if omitted.",
        rich_help_panel="Model",
    ),
    language: Optional[str] = typer.Option(
        None,
        "--language",
        "-l",
        help="Language code (en, ha, yo, fr…). Auto-detect if omitted.",
        rich_help_panel="Transcription",
    ),
    formats: str = typer.Option(
        "txt",
        "--format",
        "-f",
        help="Output format(s), comma-separated: txt,srt,vtt,json",
        rich_help_panel="Output",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file or directory. Defaults next to the source.",
        rich_help_panel="Output",
    ),
    word_timestamps: bool = typer.Option(
        False,
        "--word-timestamps",
        help="Generate word-level timestamps (slower, more detailed).",
        rich_help_panel="Transcription",
    ),
    beam_size: int = typer.Option(
        5,
        "--beam-size",
        help="Beam size for decoding.",
        rich_help_panel="Transcription",
    ),
    vad_filter: bool = typer.Option(
        True,
        "--vad/--no-vad",
        help="Enable/disable voice activity detection filter.",
        rich_help_panel="Transcription",
    ),
    recursive: bool = typer.Option(
        False,
        "--recursive",
        "-r",
        help="When given a folder, search recursively.",
        rich_help_panel="Input",
    ),
    skip_existing: bool = typer.Option(
        False,
        "--skip-existing",
        help="Skip files that already have a transcript in the target format.",
        rich_help_panel="Output",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Reduce output verbosity.",
        rich_help_panel="General",
    ),
) -> None:
    """
    Transcribe one or more video/audio files (or entire folders).

    Examples:

      video-transcriber transcribe interview.mp4

      video-transcriber transcribe *.mp4 -f srt,vtt -m medium

      video-transcriber transcribe ./lectures -r --format srt --skip-existing
    """
    fmt_list = [f.strip().lower() for f in formats.split(",") if f.strip()]
    valid_fmts = {"txt", "srt", "vtt", "json"}
    for f in fmt_list:
        if f not in valid_fmts:
            console.print(f"[red]Error:[/] Unsupported format '{f}'. Choose from: {', '.join(valid_fmts)}")
            raise typer.Exit(1)

    if not check_ffmpeg():
        console.print(
            Panel(
                "[red]ffmpeg not found[/]\n\n"
                "Install it first:\n"
                "  • macOS: [cyan]brew install ffmpeg[/]\n"
                "  • Ubuntu/Debian: [cyan]sudo apt install ffmpeg[/]\n"
                "  • Windows: [cyan]https://ffmpeg.org/download.html[/]",
                title="Missing Dependency",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    # Collect all media files
    media_files: List[Path] = []
    for item in inputs:
        if is_url(item):
            console.print(
                "[yellow]URL support requires the optional 'url' extra.[/]\n"
                "Install with: [cyan]pip install 'video-transcriber[url]'[/]\n"
                "Then use yt-dlp to download first, or open an issue to request full URL support."
            )
            raise typer.Exit(1)

        p = Path(item)
        if not p.exists():
            console.print(f"[red]Error:[/] Path not found: {item}")
            raise typer.Exit(1)

        found = discover_media(p, recursive=recursive)
        if not found and p.is_file():
            console.print(f"[red]Error:[/] Unsupported file type: {p.suffix}")
            console.print(f"Supported extensions: {', '.join(sorted(MEDIA_EXTS))}")
            raise typer.Exit(1)
        media_files.extend(found)

    if not media_files:
        console.print("[yellow]No media files found.[/]")
        raise typer.Exit(0)

    # Deduplicate while preserving order
    seen = set()
    unique_files = []
    for f in media_files:
        if f not in seen:
            seen.add(f)
            unique_files.append(f)
    media_files = unique_files

    if not quiet:
        console.print(
            Panel(
                f"[bold]{len(media_files)}[/] file(s) queued\n"
                f"Model: [cyan]{model}[/] • Device: [green]{device}[/]\n"
                f"Formats: [yellow]{', '.join(fmt_list)}[/]",
                title="Video Transcriber",
                border_style="cyan",
            )
        )

    # Load model once
    model_obj = load_model(model, device=device, compute_type=compute_type)

    success = 0
    for idx, media in enumerate(media_files, 1):
        if not quiet:
            console.rule(f"[bold]{idx}/{len(media_files)}[/]  {media.name}")

        # Determine output path
        if output is None:
            out_base = media.with_suffix("")
        elif output.is_dir() or (len(media_files) > 1 and not output.suffix):
            out_base = output / media.stem
            output.mkdir(parents=True, exist_ok=True)
        else:
            out_base = output.with_suffix("")

        # Skip existing check
        if skip_existing:
            existing = all((out_base.with_suffix(f".{fmt}")).exists() for fmt in fmt_list)
            if existing:
                if not quiet:
                    console.print(f"[dim]Skipping (already exists) → {out_base}[/]")
                success += 1
                continue

        try:
            result = transcribe_file(
                model_obj,
                media,
                language=language,
                beam_size=beam_size,
                word_timestamps=word_timestamps,
                vad_filter=vad_filter,
            )

            written = save_result(
                result,
                out_base,
                fmt_list,
                word_level=word_timestamps,
            )

            if not quiet:
                console.print(
                    f"[green]✓[/] Detected language: [bold]{result.language}[/] "
                    f"({result.language_probability:.1%}) • "
                    f"Duration: {result.duration:.1f}s"
                )
                for w in written:
                    console.print(f"   [dim]→[/] {w}")

            success += 1

        except Exception as e:
            console.print(f"[red]✗ Failed:[/] {media.name}\n   {e}")
            if not quiet:
                console.print_exception(show_locals=False)

    if not quiet:
        console.print()
        if success == len(media_files):
            console.print(f"[bold green]All done![/] {success}/{len(media_files)} succeeded.")
        else:
            console.print(
                f"[bold yellow]Finished with issues.[/] {success}/{len(media_files)} succeeded."
            )


@app.command("doctor")
def doctor() -> None:
    """Check system dependencies and environment."""
    table = Table(title="System Check", show_header=True, header_style="bold cyan")
    table.add_column("Component", style="bold")
    table.add_column("Status")
    table.add_column("Details")

    # Python
    table.add_row("Python", "[green]✓[/]", f"{sys.version.split()[0]}")

    # ffmpeg
    if check_ffmpeg():
        table.add_row("ffmpeg", "[green]✓[/]", "Found in PATH")
    else:
        table.add_row("ffmpeg", "[red]✗[/]", "Not found — required for video files")

    # CUDA / torch availability (lightweight check)
    try:
        import torch

        cuda_available = torch.cuda.is_available()
        if cuda_available:
            name = torch.cuda.get_device_name(0)
            table.add_row("CUDA", "[green]✓[/]", name)
        else:
            table.add_row("CUDA", "[yellow]—[/]", "Not available (CPU only)")
    except ImportError:
        table.add_row("CUDA", "[dim]—[/]", "torch not installed (optional)")

    # faster-whisper
    try:
        import faster_whisper

        table.add_row("faster-whisper", "[green]✓[/]", faster_whisper.__version__)
    except Exception as e:
        table.add_row("faster-whisper", "[red]✗[/]", str(e))

    console.print(table)
    console.print()
    console.print("[dim]Tip: For GPU acceleration install CUDA-enabled torch + use --device cuda[/]")


@app.command("models")
def models() -> None:
    """Show recommended Whisper models and their trade-offs."""
    table = Table(title="Recommended Models", show_header=True, header_style="bold magenta")
    table.add_column("Model", style="cyan")
    table.add_column("Params")
    table.add_column("VRAM (approx)")
    table.add_column("Relative Speed")
    table.add_column("Accuracy")
    table.add_column("Best for")

    rows = [
        ("tiny", "39 M", "~1 GB", "Very Fast", "Low", "Quick drafts, testing"),
        ("base", "74 M", "~1 GB", "Fast", "Decent", "Everyday short clips"),
        ("small", "244 M", "~2 GB", "Good", "Good", "Balanced (default)"),
        ("medium", "769 M", "~5 GB", "Medium", "High", "High quality work"),
        ("large-v2", "1550 M", "~10 GB", "Slower", "Very High", "Critical accuracy"),
        ("large-v3", "1550 M", "~10 GB", "Slower", "Best", "Maximum accuracy"),
    ]
    for row in rows:
        table.add_row(*row)

    console.print(table)
    console.print()
    console.print(
        "[dim]On CPU the 'int8' compute type is used by default for speed.\n"
        "On CUDA, 'float16' is preferred.[/]"
    )


if __name__ == "__main__":
    app()

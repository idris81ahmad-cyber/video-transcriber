"""Command-line interface for Video Transcriber."""

from __future__ import annotations

import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from video_transcriber import __version__
from video_transcriber.config import load_config
from video_transcriber.core import load_model, save_result, transcribe_file
from video_transcriber.utils import (
    MEDIA_EXTS,
    check_ffmpeg,
    check_ytdlp,
    discover_media,
    download_from_url,
    is_url,
)

# Load user config once so CLI options can use it as defaults
_CFG = load_config()

app = typer.Typer(
    name="video-transcriber",
    help="Fast, accurate, local video & audio transcription powered by Faster-Whisper.",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()


@dataclass
class Job:
    """A single transcription job (local file or downloaded URL)."""
    path: Path
    display_name: str
    is_temp: bool = False
    original_url: Optional[str] = None


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
        _CFG["model"],
        "--model",
        "-m",
        help="Whisper model size: tiny, base, small, medium, large-v2, large-v3",
        rich_help_panel="Model",
    ),
    device: str = typer.Option(
        _CFG["device"],
        "--device",
        "-d",
        help="Device to run on: cpu or cuda",
        rich_help_panel="Model",
    ),
    compute_type: Optional[str] = typer.Option(
        _CFG["compute_type"],
        "--compute-type",
        help="Quantization (int8, float16, float32…). Auto if omitted.",
        rich_help_panel="Model",
    ),
    language: Optional[str] = typer.Option(
        _CFG["language"],
        "--language",
        "-l",
        help="Language code (en, ha, yo, fr…). Auto-detect if omitted.",
        rich_help_panel="Transcription",
    ),
    formats: str = typer.Option(
        _CFG["format"],
        "--format",
        "-f",
        help="Output format(s), comma-separated: txt,srt,vtt,json",
        rich_help_panel="Output",
    ),
    output: Optional[Path] = typer.Option(
        Path(_CFG["output"]) if _CFG["output"] else None,
        "--output",
        "-o",
        help="Output file or directory. Defaults next to the source (or current dir for URLs).",
        rich_help_panel="Output",
    ),
    word_timestamps: bool = typer.Option(
        _CFG["word_timestamps"],
        "--word-timestamps",
        help="Generate word-level timestamps (slower, more detailed).",
        rich_help_panel="Transcription",
    ),
    beam_size: int = typer.Option(
        _CFG["beam_size"],
        "--beam-size",
        help="Beam size for decoding.",
        rich_help_panel="Transcription",
    ),
    vad_filter: bool = typer.Option(
        _CFG["vad"],
        "--vad/--no-vad",
        help="Enable/disable voice activity detection filter.",
        rich_help_panel="Transcription",
    ),
    diarize: bool = typer.Option(
        _CFG["diarize"],
        "--diarize/--no-diarize",
        help="Enable speaker diarization (requires [diarization] extra + HF token).",
        rich_help_panel="Transcription",
    ),
    recursive: bool = typer.Option(
        _CFG["recursive"],
        "--recursive",
        "-r",
        help="When given a folder, search recursively.",
        rich_help_panel="Input",
    ),
    skip_existing: bool = typer.Option(
        _CFG["skip_existing"],
        "--skip-existing/--no-skip-existing",
        help="Skip files that already have a transcript in the target format.",
        rich_help_panel="Output",
    ),
    quiet: bool = typer.Option(
        _CFG["quiet"],
        "--quiet",
        "-q",
        help="Reduce output verbosity.",
        rich_help_panel="General",
    ),
) -> None:
    """
    Transcribe one or more video/audio files, folders, or YouTube/URLs.

    You can also call this as the default command:

      video-transcriber interview.mp4
      video-transcriber interview.mp4 --diarize -f srt
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

    if diarize:
        from video_transcriber.diarize import check_diarization_available

        if not check_diarization_available():
            console.print(
                Panel(
                    "[red]Speaker diarization requires the optional extra[/]\n\n"
                    "Install with:\n"
                    "  [cyan]pip install 'video-transcriber[diarization]'[/]\n\n"
                    "You also need a Hugging Face token with access to the pyannote models.\n"
                    "1. Accept the conditions at:\n"
                    "   https://huggingface.co/pyannote/speaker-diarization-3.1\n"
                    "2. Create a token and set:\n"
                    "   [cyan]export HF_TOKEN=hf_...[/]",
                    title="Missing Dependency",
                    border_style="red",
                )
            )
            raise typer.Exit(1)

    # ------------------------------------------------------------------
    # Resolve all inputs into Job objects
    # ------------------------------------------------------------------
    jobs: List[Job] = []
    temp_dirs: List[Path] = []

    for item in inputs:
        if is_url(item):
            if not check_ytdlp():
                console.print(
                    Panel(
                        "[red]yt-dlp is required for URL / YouTube support[/]\n\n"
                        "Install the optional extra:\n"
                        "  [cyan]pip install 'video-transcriber[url]'[/]\n\n"
                        "or simply:\n"
                        "  [cyan]pip install yt-dlp[/]",
                        title="Missing Dependency",
                        border_style="red",
                    )
                )
                raise typer.Exit(1)

            if not quiet:
                console.print(f"[cyan]Downloading[/] {item}")

            try:
                tmp_dir = Path(tempfile.mkdtemp(prefix="vt-url-"))
                temp_dirs.append(tmp_dir)
                path, title = download_from_url(item, output_dir=tmp_dir, audio_only=True)
                jobs.append(Job(path=path, display_name=title, is_temp=True, original_url=item))
            except Exception as e:
                console.print(f"[red]✗ Download failed:[/] {item}\n   {e}")
                continue
        else:
            p = Path(item)
            if not p.exists():
                console.print(f"[red]Error:[/] Path not found: {item}")
                raise typer.Exit(1)

            found = discover_media(p, recursive=recursive)
            if not found and p.is_file():
                console.print(f"[red]Error:[/] Unsupported file type: {p.suffix}")
                console.print(f"Supported extensions: {', '.join(sorted(MEDIA_EXTS))}")
                raise typer.Exit(1)

            for f in found:
                jobs.append(Job(path=f, display_name=f.name))

    if not jobs:
        console.print("[yellow]No media to process.[/]")
        raise typer.Exit(0)

    # Deduplicate by path
    seen = set()
    unique_jobs: List[Job] = []
    for job in jobs:
        if job.path not in seen:
            seen.add(job.path)
            unique_jobs.append(job)
    jobs = unique_jobs

    if not quiet:
        extra = " • [magenta]diarization ON[/]" if diarize else ""
        console.print(
            Panel(
                f"[bold]{len(jobs)}[/] item(s) queued\n"
                f"Model: [cyan]{model}[/] • Device: [green]{device}[/]\n"
                f"Formats: [yellow]{', '.join(fmt_list)}[/]{extra}",
                title="Video Transcriber",
                border_style="cyan",
            )
        )

    # Load model once
    model_obj = load_model(model, device=device, compute_type=compute_type)

    # Load diarization pipeline once if needed
    diarization_pipeline = None
    if diarize:
        from video_transcriber.diarize import load_diarization_pipeline

        diarization_pipeline = load_diarization_pipeline(device=device)

    success = 0
    try:
        for idx, job in enumerate(jobs, 1):
            if not quiet:
                console.rule(f"[bold]{idx}/{len(jobs)}[/]  {job.display_name}")

            # Determine output base path
            if output is None:
                if job.is_temp:
                    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in job.display_name)
                    safe_name = safe_name.strip()[:80] or "transcript"
                    out_base = Path.cwd() / safe_name
                else:
                    out_base = job.path.with_suffix("")
            elif output.is_dir() or (len(jobs) > 1 and not output.suffix):
                out_base = output / (job.path.stem if not job.is_temp else job.display_name[:60])
                output.mkdir(parents=True, exist_ok=True)
            else:
                out_base = output.with_suffix("")

            # Skip existing
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
                    job.path,
                    language=language,
                    beam_size=beam_size,
                    word_timestamps=word_timestamps,
                    vad_filter=vad_filter,
                    diarize=diarize,
                    diarization_pipeline=diarization_pipeline,
                    device=device,
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
                console.print(f"[red]✗ Failed:[/] {job.display_name}\n   {e}")
                if not quiet:
                    console.print_exception(show_locals=False)

    finally:
        for d in temp_dirs:
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass

    if not quiet:
        console.print()
        if success == len(jobs):
            console.print(f"[bold green]All done![/] {success}/{len(jobs)} succeeded.")
        else:
            console.print(
                f"[bold yellow]Finished with issues.[/] {success}/{len(jobs)} succeeded."
            )


@app.command("doctor")
def doctor() -> None:
    """Check system dependencies and environment."""
    table = Table(title="System Check", show_header=True, header_style="bold cyan")
    table.add_column("Component", style="bold")
    table.add_column("Status")
    table.add_column("Details")

    table.add_row("Python", "[green]✓[/]", f"{sys.version.split()[0]}")

    if check_ffmpeg():
        table.add_row("ffmpeg", "[green]✓[/]", "Found in PATH")
    else:
        table.add_row("ffmpeg", "[red]✗[/]", "Not found — required for video files")

    if check_ytdlp():
        table.add_row("yt-dlp", "[green]✓[/]", "installed")
    else:
        table.add_row("yt-dlp", "[yellow]—[/]", "Not installed (optional — YouTube/URLs)")

    try:
        from video_transcriber.diarize import check_diarization_available

        if check_diarization_available():
            table.add_row("pyannote.audio", "[green]✓[/]", "installed (diarization ready)")
        else:
            table.add_row("pyannote.audio", "[yellow]—[/]", "Not installed (optional — --diarize)")
    except Exception:
        table.add_row("pyannote.audio", "[yellow]—[/]", "Not installed (optional — --diarize)")

    try:
        import torch

        if torch.cuda.is_available():
            table.add_row("CUDA", "[green]✓[/]", torch.cuda.get_device_name(0))
        else:
            table.add_row("CUDA", "[yellow]—[/]", "Not available (CPU only)")
    except ImportError:
        table.add_row("CUDA", "[dim]—[/]", "torch not installed (optional)")

    try:
        import faster_whisper

        table.add_row("faster-whisper", "[green]✓[/]", faster_whisper.__version__)
    except Exception as e:
        table.add_row("faster-whisper", "[red]✗[/]", str(e))

    console.print(table)
    console.print()
    console.print("[dim]Tip: For GPU acceleration install CUDA-enabled torch + use --device cuda[/]")
    console.print("[dim]Tip: For YouTube/URL support → pip install 'video-transcriber[url]'[/]")
    console.print("[dim]Tip: For speaker diarization → pip install 'video-transcriber[diarization]'[/]")


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


def run() -> None:
    """
    Entry point that makes `transcribe` the default command.

    So both of these work:

      video-transcriber interview.mp4
      video-transcriber transcribe interview.mp4
    """
    known_commands = {"transcribe", "doctor", "models"}
    # Flags that should not trigger the default command injection
    if len(sys.argv) > 1:
        first = sys.argv[1]
        if first not in known_commands and not first.startswith("-"):
            sys.argv.insert(1, "transcribe")
    app()


if __name__ == "__main__":
    run()

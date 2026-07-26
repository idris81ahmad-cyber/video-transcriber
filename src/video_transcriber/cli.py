"""Command-line interface for Video Transcriber."""

from __future__ import annotations

import shutil
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
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
        None, "--version", "-V", callback=version_callback, is_eager=True, help="Show version and exit."
    ),
) -> None:
    """Video Transcriber — local speech-to-text for video & audio."""
    pass


def _resolve_out_base(job: Job, output: Optional[Path], total_jobs: int) -> Path:
    if output is None:
        if job.is_temp:
            safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in job.display_name)
            safe_name = safe_name.strip()[:80] or "transcript"
            return Path.cwd() / safe_name
        return job.path.with_suffix("")
    if output.is_dir() or (total_jobs > 1 and not output.suffix):
        output.mkdir(parents=True, exist_ok=True)
        name = job.path.stem if not job.is_temp else job.display_name[:60]
        return output / name
    return output.with_suffix("")


@app.command("transcribe")
def transcribe(
    inputs: List[str] = typer.Argument(..., help="Media files, folders, or YouTube/URL links."),
    model: str = typer.Option(_CFG["model"], "--model", "-m", help="Whisper model size", rich_help_panel="Model"),
    device: str = typer.Option(_CFG["device"], "--device", "-d", help="cpu or cuda", rich_help_panel="Model"),
    compute_type: Optional[str] = typer.Option(_CFG["compute_type"], "--compute-type", help="Quantization type", rich_help_panel="Model"),
    language: Optional[str] = typer.Option(_CFG["language"], "--language", "-l", help="Language code", rich_help_panel="Transcription"),
    formats: str = typer.Option(_CFG["format"], "--format", "-f", help="txt,srt,vtt,json (comma-separated)", rich_help_panel="Output"),
    output: Optional[Path] = typer.Option(Path(_CFG["output"]) if _CFG["output"] else None, "--output", "-o", help="Output file or directory", rich_help_panel="Output"),
    word_timestamps: bool = typer.Option(_CFG["word_timestamps"], "--word-timestamps", help="Word-level timestamps", rich_help_panel="Transcription"),
    beam_size: int = typer.Option(_CFG["beam_size"], "--beam-size", help="Beam size", rich_help_panel="Transcription"),
    vad_filter: bool = typer.Option(_CFG["vad"], "--vad/--no-vad", help="Voice activity detection", rich_help_panel="Transcription"),
    diarize: bool = typer.Option(_CFG["diarize"], "--diarize/--no-diarize", help="Speaker diarization", rich_help_panel="Transcription"),
    recursive: bool = typer.Option(_CFG["recursive"], "--recursive", "-r", help="Search folders recursively", rich_help_panel="Input"),
    skip_existing: bool = typer.Option(_CFG["skip_existing"], "--skip-existing/--no-skip-existing", help="Skip existing transcripts", rich_help_panel="Output"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of parallel workers (1 = sequential)", rich_help_panel="Performance"),
    quiet: bool = typer.Option(_CFG["quiet"], "--quiet", "-q", help="Reduce output", rich_help_panel="General"),
) -> None:
    """
    Transcribe video/audio files, folders, or YouTube/URLs.

    Examples:

      video-transcriber interview.mp4
      video-transcriber ./lectures -r -f srt --workers 2
      video-transcriber meeting.mp4 --diarize -f srt
    """
    fmt_list = [f.strip().lower() for f in formats.split(",") if f.strip()]
    valid_fmts = {"txt", "srt", "vtt", "json"}
    for f in fmt_list:
        if f not in valid_fmts:
            console.print(f"[red]Error:[/] Unsupported format '{f}'")
            raise typer.Exit(1)

    if workers < 1:
        console.print("[red]Error:[/] --workers must be >= 1")
        raise typer.Exit(1)

    if not check_ffmpeg():
        console.print(Panel("[red]ffmpeg not found[/] — install it and add to PATH", title="Missing Dependency", border_style="red"))
        raise typer.Exit(1)

    if diarize:
        from video_transcriber.diarize import check_diarization_available
        if not check_diarization_available():
            console.print(Panel(
                "[red]Speaker diarization requires the optional extra[/]\n\n"
                "  [cyan]pip install 'video-transcriber[diarization]'[/]\n"
                "  Accept model conditions + set HF_TOKEN",
                title="Missing Dependency", border_style="red",
            ))
            raise typer.Exit(1)

    jobs: List[Job] = []
    temp_dirs: List[Path] = []

    for item in inputs:
        if is_url(item):
            if not check_ytdlp():
                console.print(Panel("[red]yt-dlp required[/] — pip install 'video-transcriber[url]'", title="Missing Dependency", border_style="red"))
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
                raise typer.Exit(1)
            for f in found:
                jobs.append(Job(path=f, display_name=f.name))

    if not jobs:
        console.print("[yellow]No media to process.[/]")
        raise typer.Exit(0)

    seen = set()
    unique: List[Job] = []
    for j in jobs:
        if j.path not in seen:
            seen.add(j.path)
            unique.append(j)
    jobs = unique

    if not quiet:
        extra = " • [magenta]diarization[/]" if diarize else ""
        worker_info = f" • [blue]{workers} worker(s)[/]" if workers > 1 else ""
        console.print(Panel(
            f"[bold]{len(jobs)}[/] item(s) queued\n"
            f"Model: [cyan]{model}[/] • Device: [green]{device}[/]\n"
            f"Formats: [yellow]{', '.join(fmt_list)}[/]{extra}{worker_info}",
            title="Video Transcriber", border_style="cyan",
        ))

    model_obj = load_model(model, device=device, compute_type=compute_type, quiet=quiet)

    diarization_pipeline = None
    if diarize:
        from video_transcriber.diarize import load_diarization_pipeline
        diarization_pipeline = load_diarization_pipeline(device=device)

    model_lock = threading.Lock()

    def process_one(job: Job) -> Tuple[bool, str, List[Path]]:
        out_base = _resolve_out_base(job, output, len(jobs))

        if skip_existing:
            existing = all((out_base.with_suffix(f".{fmt}")).exists() for fmt in fmt_list)
            if existing:
                return True, f"skipped (exists) → {out_base}", []

        try:
            with model_lock:
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
                    quiet=True,
                )

            written = save_result(result, out_base, fmt_list, word_level=word_timestamps)
            msg = (
                f"{result.language} ({result.language_probability:.0%}) • "
                f"{result.duration:.1f}s → {', '.join(str(p.name) for p in written)}"
            )
            return True, msg, written
        except Exception as e:
            return False, str(e), []

    success = 0
    failures: List[Tuple[str, str]] = []

    try:
        if workers == 1 or len(jobs) == 1:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=console,
                transient=False,
            ) as progress:
                task_id = progress.add_task("Transcribing", total=len(jobs))
                for job in jobs:
                    progress.update(task_id, description=job.display_name[:40])
                    ok, msg, _ = process_one(job)
                    if ok:
                        success += 1
                        if not quiet:
                            console.print(f"  [green]✓[/] {job.display_name} — {msg}")
                    else:
                        failures.append((job.display_name, msg))
                        console.print(f"  [red]✗[/] {job.display_name} — {msg}")
                    progress.advance(task_id)
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=console,
                transient=False,
            ) as progress:
                task_id = progress.add_task(f"Transcribing ({workers} workers)", total=len(jobs))

                with ThreadPoolExecutor(max_workers=workers) as pool:
                    futures = {pool.submit(process_one, job): job for job in jobs}
                    for future in as_completed(futures):
                        job = futures[future]
                        try:
                            ok, msg, _ = future.result()
                        except Exception as e:
                            ok, msg = False, str(e)
                        if ok:
                            success += 1
                            if not quiet:
                                console.print(f"  [green]✓[/] {job.display_name} — {msg}")
                        else:
                            failures.append((job.display_name, msg))
                            console.print(f"  [red]✗[/] {job.display_name} — {msg}")
                        progress.advance(task_id)

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
            console.print(f"[bold yellow]Finished with issues.[/] {success}/{len(jobs)} succeeded.")
            for name, err in failures:
                console.print(f"  [red]•[/] {name}: {err}")


@app.command("web")
def web(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind"),
    port: int = typer.Option(7860, "--port", "-p", help="Port"),
    share: bool = typer.Option(False, "--share", help="Create a public Gradio link"),
) -> None:
    """
    Launch the browser-based Web UI.

    Requires: pip install 'video-transcriber[web]'
    """
    try:
        from video_transcriber.web import launch
    except Exception as e:
        console.print(Panel(
            f"[red]Web UI failed to load[/]\n\n{e}\n\n"
            "Install with:\n  [cyan]pip install 'video-transcriber[web]'[/]",
            title="Missing Dependency",
            border_style="red",
        ))
        raise typer.Exit(1)

    launch(host=host, port=port, share=share)


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
        table.add_row("ffmpeg", "[red]✗[/]", "Not found")

    if check_ytdlp():
        table.add_row("yt-dlp", "[green]✓[/]", "installed")
    else:
        table.add_row("yt-dlp", "[yellow]—[/]", "optional (YouTube/URLs)")

    try:
        from video_transcriber.diarize import check_diarization_available
        if check_diarization_available():
            table.add_row("pyannote.audio", "[green]✓[/]", "diarization ready")
        else:
            table.add_row("pyannote.audio", "[yellow]—[/]", "optional (--diarize)")
    except Exception:
        table.add_row("pyannote.audio", "[yellow]—[/]", "optional (--diarize)")

    try:
        import gradio
        table.add_row("gradio", "[green]✓[/]", getattr(gradio, "__version__", "installed"))
    except ImportError:
        table.add_row("gradio", "[yellow]—[/]", "optional (web UI)")

    try:
        import torch
        if torch.cuda.is_available():
            table.add_row("CUDA", "[green]✓[/]", torch.cuda.get_device_name(0))
        else:
            table.add_row("CUDA", "[yellow]—[/]", "CPU only")
    except ImportError:
        table.add_row("CUDA", "[dim]—[/]", "torch not installed")

    try:
        import faster_whisper
        table.add_row("faster-whisper", "[green]✓[/]", faster_whisper.__version__)
    except Exception as e:
        table.add_row("faster-whisper", "[red]✗[/]", str(e))

    console.print(table)


@app.command("models")
def models() -> None:
    """Show recommended Whisper models."""
    table = Table(title="Recommended Models", header_style="bold magenta")
    table.add_column("Model", style="cyan")
    table.add_column("Params")
    table.add_column("VRAM")
    table.add_column("Speed")
    table.add_column("Accuracy")
    table.add_column("Best for")
    rows = [
        ("tiny", "39 M", "~1 GB", "Very Fast", "Low", "Drafts"),
        ("base", "74 M", "~1 GB", "Fast", "Decent", "Short clips"),
        ("small", "244 M", "~2 GB", "Good", "Good", "Default"),
        ("medium", "769 M", "~5 GB", "Medium", "High", "High quality"),
        ("large-v3", "1550 M", "~10 GB", "Slower", "Best", "Max accuracy"),
    ]
    for r in rows:
        table.add_row(*r)
    console.print(table)


def run() -> None:
    """Entry point — makes transcribe the default command."""
    known = {"transcribe", "doctor", "models", "web"}
    if len(sys.argv) > 1 and sys.argv[1] not in known and not sys.argv[1].startswith("-"):
        sys.argv.insert(1, "transcribe")
    app()


if __name__ == "__main__":
    run()

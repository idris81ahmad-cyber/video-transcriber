"""Gradio web interface for Video Transcriber."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console

console = Console()


def _check_gradio() -> None:
    try:
        import gradio  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "Web UI requires the optional [web] extra.\n"
            "Install with:\n"
            "  pip install 'video-transcriber[web]'"
        ) from e


def _transcribe_ui(
    file_obj,
    url: str,
    model_size: str,
    device: str,
    language: str,
    formats: List[str],
    word_timestamps: bool,
    diarize: bool,
    beam_size: int,
) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Core handler used by the Gradio interface.

    Returns:
        status_message, txt_path, srt_path, vtt_path, json_path
    """
    from video_transcriber.core import load_model, save_result, transcribe_file
    from video_transcriber.utils import download_from_url, is_url

    if file_obj is None and not (url and url.strip()):
        return "Please upload a file or paste a URL.", None, None, None, None

    if not formats:
        formats = ["txt"]

    tmp_dir = Path(tempfile.mkdtemp(prefix="vt-web-"))
    media_path: Optional[Path] = None
    display_name = "input"

    try:
        if file_obj is not None:
            # Gradio gives a tempfile path or a file-like object depending on version
            src = Path(file_obj if isinstance(file_obj, (str, Path)) else file_obj.name)
            media_path = tmp_dir / src.name
            shutil.copy(src, media_path)
            display_name = src.name
        elif url and url.strip():
            url = url.strip()
            if not is_url(url):
                return "Invalid URL.", None, None, None, None
            try:
                media_path, display_name = download_from_url(
                    url, output_dir=tmp_dir, audio_only=True
                )
            except Exception as e:
                return f"Download failed: {e}", None, None, None, None

        if media_path is None or not media_path.exists():
            return "No media file available.", None, None, None, None

        lang = language.strip() or None if language else None

        model = load_model(model_size, device=device, quiet=True)

        diarization_pipeline = None
        if diarize:
            from video_transcriber.diarize import (
                check_diarization_available,
                load_diarization_pipeline,
            )

            if not check_diarization_available():
                return (
                    "Diarization requires: pip install 'video-transcriber[diarization]' "
                    "and a valid HF_TOKEN.",
                    None,
                    None,
                    None,
                    None,
                )
            diarization_pipeline = load_diarization_pipeline(device=device)

        result = transcribe_file(
            model,
            media_path,
            language=lang,
            beam_size=beam_size,
            word_timestamps=word_timestamps,
            diarize=diarize,
            diarization_pipeline=diarization_pipeline,
            device=device,
            quiet=True,
        )

        out_base = tmp_dir / Path(display_name).stem
        written = save_result(result, out_base, formats, word_level=word_timestamps)

        path_map = {p.suffix.lstrip(".").lower(): str(p) for p in written}

        status = (
            f"Done \u2014 language: {result.language} "
            f"({result.language_probability:.0%}) \u2022 duration: {result.duration:.1f}s"
        )
        if diarize:
            n_speakers = len({getattr(s, "speaker", "?") for s in result.segments})
            status += f" \u2022 speakers: {n_speakers}"

        return (
            status,
            path_map.get("txt"),
            path_map.get("srt"),
            path_map.get("vtt"),
            path_map.get("json"),
        )

    except Exception as e:
        return f"Error: {e}", None, None, None, None


def build_ui():
    """Build and return the Gradio Blocks app."""
    _check_gradio()
    import gradio as gr

    with gr.Blocks(
        title="Video Transcriber",
        theme=gr.themes.Soft(),
        css=".gradio-container { max-width: 900px !important; }",
    ) as demo:
        gr.Markdown(
            """
            # Video Transcriber
            Fast local transcription powered by **Faster-Whisper**.
            Upload a file or paste a YouTube URL.
            """
        )

        with gr.Row():
            with gr.Column(scale=1):
                file_input = gr.File(
                    label="Upload video / audio",
                    file_types=[
                        ".mp4",
                        ".mov",
                        ".mkv",
                        ".webm",
                        ".mp3",
                        ".wav",
                        ".m4a",
                        ".flac",
                        ".ogg",
                    ],
                )
                url_input = gr.Textbox(
                    label="Or paste a URL (YouTube, etc.)",
                    placeholder="https://www.youtube.com/watch?v=...",
                )

                with gr.Accordion("Settings", open=True):
                    model = gr.Dropdown(
                        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
                        value="small",
                        label="Model",
                    )
                    device = gr.Radio(choices=["cpu", "cuda"], value="cpu", label="Device")
                    language = gr.Textbox(
                        label="Language (leave empty for auto-detect)",
                        placeholder="en, ha, yo, fr, …",
                    )
                    formats = gr.CheckboxGroup(
                        choices=["txt", "srt", "vtt", "json"],
                        value=["txt", "srt"],
                        label="Output formats",
                    )
                    word_timestamps = gr.Checkbox(label="Word-level timestamps", value=False)
                    diarize = gr.Checkbox(label="Speaker diarization", value=False)
                    beam_size = gr.Slider(1, 10, value=5, step=1, label="Beam size")

                run_btn = gr.Button("Transcribe", variant="primary")

            with gr.Column(scale=1):
                status = gr.Textbox(label="Status", interactive=False)
                out_txt = gr.File(label="TXT")
                out_srt = gr.File(label="SRT")
                out_vtt = gr.File(label="VTT")
                out_json = gr.File(label="JSON")

        run_btn.click(
            fn=_transcribe_ui,
            inputs=[
                file_input,
                url_input,
                model,
                device,
                language,
                formats,
                word_timestamps,
                diarize,
                beam_size,
            ],
            outputs=[status, out_txt, out_srt, out_vtt, out_json],
        )

        gr.Markdown(
            """
            ---
            **Tips**
            - First run downloads the Whisper model (cached afterwards).
            - For speaker diarization install `[diarization]` extra and set `HF_TOKEN`.
            - For YouTube URLs install `[url]` extra (`yt-dlp`).
            """
        )

    return demo


def launch(
    host: str = "127.0.0.1",
    port: int = 7860,
    share: bool = False,
) -> None:
    """Launch the Gradio web UI."""
    demo = build_ui()
    console.print(f"[bold cyan]Starting Web UI[/] on http://{host}:{port}")
    demo.launch(server_name=host, server_port=port, share=share)

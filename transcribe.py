#!/usr/bin/env python3
"""
Video / Audio Transcriber using Faster-Whisper
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel
from tqdm import tqdm


SUPPORTED_VIDEO_EXTS = {'.mp4', '.mov', '.mkv', '.webm', '.avi', '.flv', '.m4v'}
SUPPORTED_AUDIO_EXTS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma'}


def extract_audio(video_path: Path, output_path: Path) -> None:
    """Extract audio track from video using ffmpeg."""
    cmd = [
        'ffmpeg',
        '-y',
        '-i', str(video_path),
        '-vn',
        '-acodec', 'pcm_s16le',
        '-ar', '16000',
        '-ac', '1',
        str(output_path),
    ]
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        print("Error: ffmpeg not found. Please install ffmpeg and make sure it is in your PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e}")
        sys.exit(1)


def format_timestamp(seconds: float, always_include_hours: bool = False) -> str:
    """Convert seconds to SRT/VTT timestamp format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)

    if always_include_hours or hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    return f"{minutes:02d}:{secs:02d},{millis:03d}"


def write_txt(segments, output_path: Path) -> None:
    with open(output_path, 'w', encoding='utf-8') as f:
        for segment in segments:
            f.write(segment.text.strip() + "\n")


def write_srt(segments, output_path: Path) -> None:
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments, start=1):
            start = format_timestamp(segment.start, always_include_hours=True)
            end = format_timestamp(segment.end, always_include_hours=True)
            # SRT uses comma for milliseconds
            start = start.replace('.', ',')
            end = end.replace('.', ',')
            f.write(f"{i}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{segment.text.strip()}\n\n")


def write_vtt(segments, output_path: Path) -> None:
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("WEBVTT\n\n")
        for segment in segments:
            start = format_timestamp(segment.start, always_include_hours=True).replace(',', '.')
            end = format_timestamp(segment.end, always_include_hours=True).replace(',', '.')
            f.write(f"{start} --> {end}\n")
            f.write(f"{segment.text.strip()}\n\n")


def write_json(segments, output_path: Path, language: Optional[str] = None) -> None:
    data = {
        "language": language,
        "segments": [
            {
                "id": i,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
            }
            for i, segment in enumerate(segments)
        ],
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe video or audio files using Faster-Whisper",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", type=str, help="Path to video or audio file")
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output file path (default: same name as input with new extension)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="small",
        choices=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
        help="Whisper model size",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        choices=["cpu", "cuda"],
        help="Device to run inference on",
    )
    parser.add_argument(
        "--compute-type",
        type=str,
        default=None,
        help="Quantization type (e.g. int8, float16, float32). Auto-selected if omitted.",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        help="Language code (e.g. en, ha, yo, fr). Auto-detect if omitted.",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="txt",
        choices=["txt", "srt", "vtt", "json"],
        help="Output format",
    )
    parser.add_argument(
        "--word-timestamps",
        action="store_true",
        help="Include word-level timestamps (slower, more detailed)",
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="Beam size for decoding",
    )
    parser.add_argument(
        "--vad-filter",
        action="store_true",
        default=True,
        help="Enable voice activity detection filter",
    )
    parser.add_argument(
        "--no-vad-filter",
        action="store_false",
        dest="vad_filter",
        help="Disable VAD filter",
    )

    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    suffix = input_path.suffix.lower()
    is_video = suffix in SUPPORTED_VIDEO_EXTS
    is_audio = suffix in SUPPORTED_AUDIO_EXTS

    if not (is_video or is_audio):
        print(f"Error: Unsupported file type: {suffix}")
        print(f"Supported: {', '.join(sorted(SUPPORTED_VIDEO_EXTS | SUPPORTED_AUDIO_EXTS))}")
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix(f".{args.format}")

    # Determine compute type
    compute_type = args.compute_type
    if compute_type is None:
        compute_type = "float16" if args.device == "cuda" else "int8"

    print(f"Loading model '{args.model}' on {args.device} ({compute_type})...")
    model = WhisperModel(
        args.model,
        device=args.device,
        compute_type=compute_type,
    )

    # Prepare audio file
    temp_audio = None
    audio_path = input_path

    if is_video:
        print("Extracting audio from video...")
        temp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_audio.close()
        extract_audio(input_path, Path(temp_audio.name))
        audio_path = Path(temp_audio.name)

    try:
        print(f"Transcribing: {input_path.name}")
        segments_generator, info = model.transcribe(
            str(audio_path),
            language=args.language,
            beam_size=args.beam_size,
            word_timestamps=args.word_timestamps,
            vad_filter=args.vad_filter,
        )

        print(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")

        # Collect segments with a progress bar
        segments = []
        for segment in tqdm(segments_generator, desc="Transcribing", unit="seg"):
            segments.append(segment)

        # Write output
        print(f"Writing {args.format.upper()} → {output_path}")
        if args.format == "txt":
            write_txt(segments, output_path)
        elif args.format == "srt":
            write_srt(segments, output_path)
        elif args.format == "vtt":
            write_vtt(segments, output_path)
        elif args.format == "json":
            write_json(segments, output_path, language=info.language)

        print("Done!")

    finally:
        if temp_audio is not None:
            try:
                os.unlink(temp_audio.name)
            except OSError:
                pass


if __name__ == "__main__":
    main()

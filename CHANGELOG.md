# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-07-26

### Added
- **Speaker diarization** via `pyannote.audio` (optional `[diarization]` extra)
- `--diarize` CLI flag
- Speaker labels in TXT, SRT, VTT and JSON outputs (`[SPEAKER_00]`, `[SPEAKER_01]`, …)
- `doctor` command now checks for pyannote availability

### Notes
- Requires accepting the pyannote model conditions on Hugging Face and setting `HF_TOKEN`

## [1.0.0] - 2026-07-26

### Added
- Initial public release
- Fast local transcription using Faster-Whisper
- Support for video and audio files (MP4, MOV, MKV, WebM, MP3, WAV, etc.)
- YouTube and general URL support via optional `yt-dlp` extra
- Multiple export formats: TXT, SRT, VTT, JSON
- Word-level timestamps
- Batch processing of folders (recursive)
- Skip already transcribed files
- Beautiful CLI powered by Typer + Rich
- `doctor` and `models` commands
- Automatic language detection
- CPU and CUDA support

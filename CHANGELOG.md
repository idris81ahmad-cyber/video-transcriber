# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-07-26

### Added
- **Concurrent batch processing** with `--workers N`
- Unified Rich progress bar for batch jobs (overall + current file + ETA)
- Thread-safe model access (safe on both CPU and GPU)

## [1.2.0] - 2026-07-26

### Added
- **Default command**: `video-transcriber interview.mp4` works without typing `transcribe`
- **Config file support** (`video-transcriber.toml` / `~/.config/video-transcriber/config.toml`)

## [1.1.0] - 2026-07-26

### Added
- **Speaker diarization** via pyannote.audio (`--diarize`)
- Speaker labels in all export formats

## [1.0.0] - 2026-07-26

### Added
- Initial release with Faster-Whisper, YouTube support, multiple formats, batch folders

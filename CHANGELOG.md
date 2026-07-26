# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.1] - 2026-07-26

### Added
- **CSV export** (`-f csv`) with optional speaker column
- Unit test suite for utils, exporters, and CLI helpers
- CI step runs `pytest` on Python 3.10–3.12

### Changed
- Safer URL detection and filename sanitization for YouTube titles
- Lazy-load Faster-Whisper so `--version` / `doctor` work without native DLLs
- Export writers create parent directories automatically

## [1.4.0] - 2026-07-26

### Added
- **Web UI** powered by Gradio (`video-transcriber web`)
- Optional `[web]` extra
- Browser upload + YouTube URL + settings + downloadable outputs

## [1.3.0] - 2026-07-26

### Added
- Concurrent batch processing (`--workers N`)
- Unified Rich progress bar for batch jobs

## [1.2.0] - 2026-07-26

### Added
- Default command (no need to type `transcribe`)
- Config file support

## [1.1.0] - 2026-07-26

### Added
- Speaker diarization (`--diarize`)

## [1.0.0] - 2026-07-26

### Added
- Initial release

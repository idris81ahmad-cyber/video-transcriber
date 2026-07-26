"""Tests for utility helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from video_transcriber.utils import (
    discover_media,
    format_timestamp,
    is_url,
    sanitize_filename,
)


class TestFormatTimestamp:
    def test_zero(self):
        assert format_timestamp(0) == "00:00:00,000"

    def test_seconds_with_millis(self):
        assert format_timestamp(1.5) == "00:00:01,500"

    def test_vtt_decimal_marker(self):
        assert format_timestamp(1.234, decimal_marker=".") == "00:00:01.234"

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            format_timestamp(-0.1)


class TestIsUrl:
    def test_https(self):
        assert is_url("https://www.youtube.com/watch?v=abc")

    def test_www_prefix(self):
        assert is_url("www.youtube.com/watch?v=abc")

    def test_local_path(self):
        assert not is_url("interview.mp4")
        assert not is_url("./folder/file.mp3")

    def test_empty(self):
        assert not is_url("")


class TestSanitizeFilename:
    def test_strips_illegal_chars(self):
        assert ":" not in sanitize_filename('a:b/c*d?"')

    def test_empty_fallback(self):
        assert sanitize_filename("   ") == "transcript"


class TestDiscoverMedia:
    def test_single_file(self, tmp_path: Path):
        f = tmp_path / "clip.mp4"
        f.write_bytes(b"x")
        assert discover_media(f) == [f]

    def test_directory_recursive(self, tmp_path: Path):
        (tmp_path / "a.mp3").write_bytes(b"x")
        nested = tmp_path / "sub"
        nested.mkdir()
        (nested / "b.wav").write_bytes(b"x")
        found = discover_media(tmp_path, recursive=True)
        assert {p.name for p in found} == {"a.mp3", "b.wav"}

"""Tests for output exporters."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from video_transcriber.exporters import (
    export,
    write_csv,
    write_json,
    write_srt,
    write_txt,
    write_vtt,
)


def test_write_txt_includes_speaker(tmp_path: Path, sample_segments):
    out = tmp_path / "out.txt"
    write_txt(sample_segments, out)
    text = out.read_text(encoding="utf-8")
    assert "[SPEAKER_00] Hello world." in text
    assert "[SPEAKER_01] This is a test." in text


def test_write_srt_segment_level(tmp_path: Path, sample_segments):
    out = tmp_path / "out.srt"
    write_srt(sample_segments, out, word_level=False)
    text = out.read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:02,500" in text
    assert "[SPEAKER_00] Hello world." in text


def test_write_vtt(tmp_path: Path, sample_segments):
    out = tmp_path / "out.vtt"
    write_vtt(sample_segments, out)
    text = out.read_text(encoding="utf-8")
    assert text.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:02.500" in text


def test_write_json_with_speakers(tmp_path: Path, sample_segments):
    out = tmp_path / "out.json"
    write_json(
        sample_segments,
        out,
        language="en",
        language_probability=0.98,
        duration=5.0,
        word_level=True,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["language"] == "en"
    assert data["segments"][0]["speaker"] == "SPEAKER_00"
    assert "words" in data["segments"][0]


def test_write_csv_segments(tmp_path: Path, sample_segments):
    out = tmp_path / "out.csv"
    write_csv(sample_segments, out, word_level=False)
    with out.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["index", "start", "end", "speaker", "text"]
    assert rows[1][3] == "SPEAKER_00"
    assert rows[1][4] == "Hello world."


def test_export_creates_parent_dirs(tmp_path: Path, sample_segments):
    path = tmp_path / "a" / "b" / "c.srt"
    export(sample_segments, path, "srt")
    assert path.exists()


def test_export_unsupported(tmp_path: Path, sample_segments):
    with pytest.raises(ValueError, match="Unsupported format"):
        export(sample_segments, tmp_path / "x.foo", "foo")

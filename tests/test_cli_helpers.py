"""Lightweight CLI helper tests (no model download)."""

from __future__ import annotations

from typer.testing import CliRunner

from video_transcriber import __version__
from video_transcriber.cli import app
from video_transcriber.exporters import SUPPORTED_FORMATS

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_models_command():
    result = runner.invoke(app, ["models"])
    assert result.exit_code == 0
    assert "small" in result.stdout


def test_doctor_command():
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Python" in result.stdout


def test_transcribe_bad_format():
    result = runner.invoke(app, ["transcribe", "missing.mp4", "-f", "docx"])
    assert result.exit_code == 1
    assert "Unsupported format" in result.stdout


def test_supported_formats_include_csv():
    assert "csv" in SUPPORTED_FORMATS

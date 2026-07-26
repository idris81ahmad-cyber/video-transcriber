"""Shared test fixtures."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest


@dataclass
class FakeWord:
    word: str
    start: float | None
    end: float | None
    probability: float | None = 0.9


@dataclass
class FakeSegment:
    start: float
    end: float
    text: str
    words: list[FakeWord] = field(default_factory=list)
    speaker: str | None = None


@pytest.fixture
def sample_segments() -> list[FakeSegment]:
    return [
        FakeSegment(
            start=0.0,
            end=2.5,
            text=" Hello world.",
            speaker="SPEAKER_00",
            words=[
                FakeWord(" Hello", 0.0, 1.0, 0.95),
                FakeWord(" world.", 1.0, 2.5, 0.92),
            ],
        ),
        FakeSegment(
            start=2.5,
            end=5.0,
            text=" This is a test.",
            speaker="SPEAKER_01",
            words=[
                FakeWord(" This", 2.5, 3.0, 0.9),
                FakeWord(" is", 3.0, 3.3, 0.88),
                FakeWord(" a", 3.3, 3.5, 0.85),
                FakeWord(" test.", 3.5, 5.0, 0.93),
            ],
        ),
    ]

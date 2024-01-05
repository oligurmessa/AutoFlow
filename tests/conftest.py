from __future__ import annotations

from pathlib import Path

import pytest

from autoflow.actions import Context
from autoflow.backends import FakeBackend


class FakeClock:
    """Time that only moves when something 'sleeps', so tests never wait."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def backend() -> FakeBackend:
    return FakeBackend()


@pytest.fixture
def ctx(backend: FakeBackend, clock: FakeClock, tmp_path: Path) -> Context:
    return Context(
        backend=backend,
        base_dir=tmp_path,
        sleep=clock.sleep,
        clock=clock,
        default_timeout=5,
        poll_interval=0.5,
    )


@pytest.fixture
def image(tmp_path: Path) -> str:
    """An image file that exists on disk (its contents don't matter to FakeBackend)."""
    (tmp_path / "button.png").write_bytes(b"fake png")
    return "button.png"

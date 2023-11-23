"""Backends are the only code that actually touches the mouse, keyboard and screen.

Actions talk to a Backend instead of calling pyautogui directly. That gives us:

* PyAutoGUIBackend - the real thing.
* FakeBackend      - records every call, so tests run anywhere (even in CI
                     with no screen) and never move your mouse.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from . import platform

Point = tuple[int, int]


class Backend(Protocol):
    def open_app(self, name: str) -> None: ...
    def press(self, key: str, presses: int = 1) -> None: ...
    def hotkey(self, *keys: str) -> None: ...
    def write(self, text: str, interval: float = 0.0) -> None: ...
    def click(self, x: int, y: int, clicks: int = 1, button: str = "left") -> None: ...
    def move_to(self, x: int, y: int) -> None: ...
    def scroll(self, amount: int) -> None: ...
    def locate_center(self, image: Path, confidence: float) -> Point | None: ...
    def screenshot(self, path: Path) -> None: ...




@dataclass
class FakeBackend:
    """A pretend desktop for tests and experiments.

    `visible` maps an image file name to where it "appears" on screen.
    `appear_after` lets an image show up only after N lookups, to test waiting.
    """

    visible: dict[str, Point] = field(default_factory=dict)
    appear_after: dict[str, int] = field(default_factory=dict)
    calls: list[tuple[str, Any]] = field(default_factory=list)
    _lookups: dict[str, int] = field(default_factory=dict)

    def open_app(self, name: str) -> None:
        self.calls.append(("open_app", name))

    def press(self, key: str, presses: int = 1) -> None:
        self.calls.append(("press", (key, presses)))

    def hotkey(self, *keys: str) -> None:
        self.calls.append(("hotkey", keys))

    def write(self, text: str, interval: float = 0.0) -> None:
        self.calls.append(("write", text))

    def click(self, x: int, y: int, clicks: int = 1, button: str = "left") -> None:
        self.calls.append(("click", (x, y, clicks, button)))

    def move_to(self, x: int, y: int) -> None:
        self.calls.append(("move_to", (x, y)))

    def scroll(self, amount: int) -> None:
        self.calls.append(("scroll", amount))

    def locate_center(self, image: Path, confidence: float) -> Point | None:
        name = Path(image).name
        self._lookups[name] = self._lookups.get(name, 0) + 1
        if self._lookups[name] <= self.appear_after.get(name, 0):
            return None
        return self.visible.get(name)

    def screenshot(self, path: Path) -> None:
        self.calls.append(("screenshot", str(path)))

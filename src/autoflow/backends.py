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


class PyAutoGUIBackend:
    """Controls the real desktop through pyautogui."""

    def __init__(self) -> None:
        # Imported here, not at the top of the file: pyautogui needs a display,
        # and we don't want `autoflow validate` or the tests to require one.
        import pyautogui

        self._gui = pyautogui
        # Slam the mouse into a screen corner to abort a runaway workflow.
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05
        self._scale: float | None = None

    def open_app(self, name: str) -> None:
        platform.open_app(name)

    def press(self, key: str, presses: int = 1) -> None:
        self._gui.press(key, presses=presses)

    def hotkey(self, *keys: str) -> None:
        self._gui.hotkey(*keys)

    def write(self, text: str, interval: float = 0.0) -> None:
        self._gui.write(text, interval=interval)

    def click(self, x: int, y: int, clicks: int = 1, button: str = "left") -> None:
        self._gui.click(x, y, clicks=clicks, button=button)

    def move_to(self, x: int, y: int) -> None:
        self._gui.moveTo(x, y, duration=0.2)

    def scroll(self, amount: int) -> None:
        self._gui.scroll(amount)

    def locate_center(self, image: Path, confidence: float) -> Point | None:
        try:
            box = self._gui.locateOnScreen(str(image), confidence=confidence)
        except self._gui.ImageNotFoundException:
            # Newer pyautogui versions raise instead of returning None.
            return None
        if box is None:
            return None
        x, y = self._gui.center(box)
        scale = self._retina_scale()
        return round(x / scale), round(y / scale)

    def screenshot(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._gui.screenshot(str(path))

    def _retina_scale(self) -> float:
        """Screenshots are in physical pixels, clicks are in logical points.

        On a Retina Mac the screenshot is twice as wide as the "screen size",
        so a match found at pixel (800, 600) must be clicked at (400, 300).
        """
        if self._scale is None:
            shot_width = self._gui.screenshot().width
            screen_width = self._gui.size().width
            self._scale = shot_width / screen_width if screen_width else 1.0
        return self._scale


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

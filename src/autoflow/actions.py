"""Every step type a workflow can use.

To add a new action, write a function whose first parameter is the run
Context and decorate it with @action("name"). Its other parameters become
the options a workflow can pass, and its type hints are used to validate
workflow files before anything runs. Nothing else needs to change.
"""

from __future__ import annotations

import inspect
import logging
import time
import types
import typing
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .backends import Backend, Point
from .errors import ImageNotFound, StepFailed

log = logging.getLogger("autoflow")


@dataclass
class Context:
    """Everything an action needs while a workflow runs."""

    backend: Backend
    base_dir: Path = field(default_factory=Path.cwd)
    default_timeout: float = 10.0
    default_confidence: float = 0.8
    poll_interval: float = 0.5
    # Injected so tests can fake time instead of really sleeping.
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic

    def resolve(self, path: str) -> Path:
        """Paths in a workflow are relative to the workflow file, not the shell."""
        p = Path(path).expanduser()
        return p if p.is_absolute() else self.base_dir / p


@dataclass(frozen=True)
class ActionSpec:
    name: str
    func: Callable[..., Any]
    summary: str
    params: dict[str, inspect.Parameter]
    hints: dict[str, Any]

    @property
    def primary(self) -> str | None:
        """The parameter that a short form like `- press: enter` fills in."""
        return next(iter(self.params), None)

    @property
    def required(self) -> list[str]:
        return [n for n, p in self.params.items() if p.default is inspect.Parameter.empty]

    def signature(self) -> str:
        parts = []
        for name, param in self.params.items():
            if param.default is inspect.Parameter.empty:
                parts.append(name)
            else:
                parts.append(f"{name}={param.default!r}")
        return f"{self.name}({', '.join(parts)})"


REGISTRY: dict[str, ActionSpec] = {}


def action(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a function as a workflow action."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        params = dict(inspect.signature(func).parameters)
        params.pop(next(iter(params)))  # drop the Context parameter
        hints = typing.get_type_hints(func)
        summary = (inspect.getdoc(func) or "").splitlines()[0] if func.__doc__ else ""
        REGISTRY[name] = ActionSpec(name, func, summary, params, hints)
        return func

    return decorator






# --------------------------------------------------------------------------
# Apps and waiting
# --------------------------------------------------------------------------


@action("open_app")
def open_app(ctx: Context, app: str, wait: float = 2.0) -> None:
    """Open (or bring to the front) an application by name."""
    ctx.backend.open_app(app)
    ctx.sleep(wait)


@action("open_url")
def open_url(ctx: Context, url: str) -> None:
    """Open a web page in the default browser."""
    if not webbrowser.open(url):
        raise StepFailed(f"no browser could open {url}")


@action("wait")
def wait(ctx: Context, seconds: float) -> None:
    """Pause for a fixed number of seconds. Prefer wait_for_image when you can."""
    ctx.sleep(seconds)


@action("log")
def log_message(ctx: Context, message: str) -> None:
    """Print a message to the run log."""
    log.info("  %s", message)


# --------------------------------------------------------------------------
# Keyboard
# --------------------------------------------------------------------------


@action("type")
def type_text(ctx: Context, text: str, interval: float = 0.02) -> None:
    """Type text as if on the keyboard."""
    ctx.backend.write(text, interval=interval)


@action("press")
def press(ctx: Context, key: str, times: int = 1) -> None:
    """Press a single key such as enter, tab, esc, up or f5."""
    ctx.backend.press(key, presses=times)


@action("hotkey")
def hotkey(ctx: Context, keys: str | list[str]) -> None:
    """Press a key combination, e.g. "command+space" or [ctrl, shift, t]."""
    parts = keys.split("+") if isinstance(keys, str) else keys
    ctx.backend.hotkey(*(k.strip().lower() for k in parts))


# --------------------------------------------------------------------------
# Mouse
# --------------------------------------------------------------------------

BUTTONS = ("left", "right", "middle")


@action("click")
def click(ctx: Context, x: int, y: int, clicks: int = 1, button: str = "left") -> None:
    """Click at fixed screen coordinates."""
    if button not in BUTTONS:
        raise StepFailed(f"button must be one of {', '.join(BUTTONS)}")
    ctx.backend.click(x, y, clicks=clicks, button=button)


@action("move_to")
def move_to(ctx: Context, x: int, y: int) -> None:
    """Move the mouse to fixed screen coordinates."""
    ctx.backend.move_to(x, y)


@action("scroll")
def scroll(ctx: Context, amount: int) -> None:
    """Scroll the mouse wheel; positive is up, negative is down."""
    ctx.backend.scroll(amount)


# --------------------------------------------------------------------------
# Screen
# --------------------------------------------------------------------------







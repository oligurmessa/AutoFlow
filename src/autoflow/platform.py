"""Operating-system specific helpers.

Opening an app works differently on every OS. Instead of simulating
keystrokes (Cmd+Space, type, Enter), which breaks when the UI is slow,
we ask the OS directly.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

from .errors import StepFailed


def open_app(name: str) -> None:
    """Launch (or focus) an application by name."""
    if sys.platform == "darwin":
        command = ["open", "-a", name]
    elif sys.platform == "win32":
        # `start` is a cmd.exe built-in; the empty "" is the window title.
        command = ["cmd", "/c", "start", "", name]
    else:
        launcher = shutil.which("gtk-launch")
        command = [launcher, name.lower()] if launcher else [name.lower()]

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise StepFailed(f"could not open {name!r}: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        raise StepFailed(f"could not open {name!r}: {detail}")

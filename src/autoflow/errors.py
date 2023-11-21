"""Exception types used across AutoFlow.

Everything inherits from AutoflowError so the CLI can catch one type and
print a friendly message instead of a traceback.
"""

from __future__ import annotations


class AutoflowError(Exception):
    """Base class for all expected AutoFlow errors."""


class WorkflowError(AutoflowError):
    """The workflow file is invalid (bad YAML, unknown action, missing variable...)."""

    def __init__(self, message: str, *, source: str | None = None, step: int | None = None):
        location = []
        if source:
            location.append(source)
        if step is not None:
            location.append(f"step {step}")
        prefix = f"{', '.join(location)}: " if location else ""
        super().__init__(prefix + message)
        self.source = source
        self.step = step


class StepFailed(AutoflowError):
    """A step raised an error while running (after all retries)."""


class ImageNotFound(StepFailed):
    """An on-screen image could not be found before the timeout."""

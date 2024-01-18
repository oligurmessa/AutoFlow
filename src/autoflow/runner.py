"""Run a parsed Workflow step by step, with retries, logging and failure screenshots."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .actions import REGISTRY, Context
from .errors import AutoflowError
from .workflow import Step, Workflow

log = logging.getLogger("autoflow")


@dataclass
class StepResult:
    step: Step
    ok: bool
    attempts: int = 0
    seconds: float = 0.0
    error: str | None = None
    skipped: bool = False  # optional step that failed


@dataclass
class RunResult:
    workflow: Workflow
    results: list[StepResult] = field(default_factory=list)
    screenshot: Path | None = None

    @property
    def ok(self) -> bool:
        return all(r.ok or r.skipped for r in self.results)

    @property
    def failed(self) -> StepResult | None:
        return next((r for r in self.results if not r.ok and not r.skipped), None)


class Runner:
    def __init__(
        self,
        ctx: Context,
        *,
        dry_run: bool = False,
        retry_delay: float = 1.0,
        failure_dir: Path | None = Path("autoflow-failures"),
    ) -> None:
        self.ctx = ctx
        self.dry_run = dry_run
        self.retry_delay = retry_delay
        self.failure_dir = failure_dir

    def run(self, workflow: Workflow) -> RunResult:
        run = RunResult(workflow)
        total = len(workflow.steps)
        log.info("▶ %s (%d steps)%s", workflow.name, total, "  [dry run]" if self.dry_run else "")

        for step in workflow.steps:
            label = f"[{step.index}/{total}] {step.describe()}"
            if self.dry_run:
                extras = []
                if step.retries:
                    extras.append(f"retries={step.retries}")
                if step.optional:
                    extras.append("optional")
                log.info("  %s%s", label, f"  ({', '.join(extras)})" if extras else "")
                run.results.append(StepResult(step, ok=True))
                continue

            log.info("  %s", label)
            result = self._run_step(step)
            run.results.append(result)

            if result.ok:
                log.debug("    done in %.2fs", result.seconds)
            elif step.optional:
                result.skipped = True
                log.warning("    ⚠ optional step failed, continuing: %s", result.error)
            else:
                log.error("    ✖ %s", result.error)
                run.screenshot = self._save_failure_screenshot(step)
                break

        if run.ok:
            log.info("✔ finished %s", workflow.name)
        return run

    def _run_step(self, step: Step) -> StepResult:
        spec = REGISTRY[step.action]
        start = time.monotonic()
        attempts = step.retries + 1
        error = ""

        for attempt in range(1, attempts + 1):
            try:
                spec.func(self.ctx, **step.params)
                return StepResult(step, ok=True, attempts=attempt, seconds=time.monotonic() - start)
            except AutoflowError as exc:
                error = str(exc)
            except Exception as exc:
                # pyautogui's failsafe means "the human wants this to stop" - never retry.
                if type(exc).__name__ == "FailSafeException":
                    return StepResult(
                        step,
                        ok=False,
                        attempts=attempt,
                        error="aborted: mouse moved to a screen corner (failsafe)",
                    )
                error = f"{type(exc).__name__}: {exc}"

            if attempt < attempts:
                log.warning("    attempt %d/%d failed: %s - retrying", attempt, attempts, error)
                self.ctx.sleep(self.retry_delay)

        return StepResult(
            step, ok=False, attempts=attempts, seconds=time.monotonic() - start, error=error
        )

    def _save_failure_screenshot(self, step: Step) -> Path | None:
        if self.failure_dir is None:
            return None
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = self.failure_dir / f"{stamp}-step{step.index}-{step.action}.png"
        try:
            self.ctx.backend.screenshot(path)
        except Exception as exc:  # a failing screenshot must not hide the real error
            log.debug("could not save failure screenshot: %s", exc)
            return None
        log.error("    screenshot saved to %s", path)
        return path

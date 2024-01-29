"""Command-line interface: `autoflow run | validate | actions`."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .actions import REGISTRY, Context
from .backends import Backend, FakeBackend
from .errors import AutoflowError, WorkflowError
from .runner import Runner
from .workflow import load_workflow

log = logging.getLogger("autoflow")

EXIT_OK = 0
EXIT_STEP_FAILED = 1
EXIT_INVALID = 2


def parse_var(text: str) -> tuple[str, str]:
    name, sep, value = text.partition("=")
    if not sep or not name:
        raise argparse.ArgumentTypeError(f"expected NAME=VALUE, got {text!r}")
    return name.strip(), value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autoflow",
        description="Automate repetitive desktop tasks with simple YAML workflows.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug output")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a workflow")
    run.add_argument("workflow", type=Path, help="path to a .yaml workflow")
    run.add_argument(
        "--var",
        action="append",
        type=parse_var,
        default=[],
        metavar="NAME=VALUE",
        help="set or override a workflow variable (repeatable)",
    )
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="print the steps without touching the mouse or keyboard",
    )
    run.add_argument(
        "--countdown",
        type=float,
        default=3.0,
        metavar="SECONDS",
        help="delay before starting, so you can let go of the mouse (default 3)",
    )
    run.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        metavar="SECONDS",
        help="default time to wait for images (default 10)",
    )
    run.add_argument(
        "--confidence",
        type=float,
        default=0.8,
        help="default image match confidence between 0 and 1 (default 0.8)",
    )

    validate = sub.add_parser("validate", help="check workflow files without running them")
    validate.add_argument("paths", nargs="+", type=Path, help="workflow files or folders")

    sub.add_parser("actions", help="list every available step type")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )
    try:
        if args.command == "run":
            return cmd_run(args)
        if args.command == "validate":
            return cmd_validate(args.paths)
        return cmd_actions()
    except WorkflowError as exc:
        log.error("error: %s", exc)
        return EXIT_INVALID
    except AutoflowError as exc:
        log.error("error: %s", exc)
        return EXIT_STEP_FAILED
    except KeyboardInterrupt:
        log.error("\ninterrupted")
        return 130


def cmd_run(args: argparse.Namespace) -> int:
    workflow = load_workflow(args.workflow, overrides=dict(args.var))

    if not args.dry_run:
        missing = workflow.missing_images()
        if missing:
            for path in missing:
                log.error("error: image not found: %s", path)
            log.error("Capture these screenshots first - see docs/writing-workflows.md")
            return EXIT_INVALID

    backend: Backend = FakeBackend() if args.dry_run else _real_backend()
    ctx = Context(
        backend=backend,
        base_dir=workflow.base_dir,
        default_timeout=args.timeout,
        default_confidence=args.confidence,
    )

    if not args.dry_run and args.countdown > 0:
        log.info("Starting in %gs - move the mouse into a screen corner to abort.", args.countdown)
        time.sleep(args.countdown)

    result = Runner(ctx, dry_run=args.dry_run).run(workflow)
    return EXIT_OK if result.ok else EXIT_STEP_FAILED


def _real_backend() -> Backend:
    try:
        from .backends import PyAutoGUIBackend

        return PyAutoGUIBackend()
    except ImportError as exc:
        raise AutoflowError(
            f"could not load pyautogui ({exc}). Install with: pip install -e ."
        ) from exc
    except Exception as exc:  # e.g. no display available on Linux
        raise AutoflowError(f"could not start desktop control: {exc}") from exc


def _workflow_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*") if p.suffix in {".yaml", ".yml"}))
        else:
            files.append(path)
    return files


def cmd_validate(paths: list[Path]) -> int:
    files = _workflow_files(paths)
    if not files:
        log.error("no .yaml workflow files found")
        return EXIT_INVALID

    invalid = 0
    for file in files:
        try:
            workflow = load_workflow(file)
        except WorkflowError as exc:
            invalid += 1
            log.error("✖ %s", exc)
            continue
        log.info("✔ %s - %s (%d steps)", file, workflow.name, len(workflow.steps))
        for path in workflow.missing_images():
            log.warning("    ⚠ image not captured yet: %s", path)

    log.info("\n%d file(s) checked, %d invalid", len(files), invalid)
    return EXIT_INVALID if invalid else EXIT_OK


def cmd_actions() -> int:
    width = max(len(name) for name in REGISTRY)
    for name in sorted(REGISTRY):
        spec = REGISTRY[name]
        print(f"{name:<{width}}  {spec.summary}")
        print(f"{'':<{width}}  {spec.signature()}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())

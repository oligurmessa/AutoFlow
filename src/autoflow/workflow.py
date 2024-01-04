"""Load workflow YAML files and turn them into validated Step objects.

A workflow looks like this:

    name: Play a song
    vars:
      song: My 1st Song
    steps:
      - open_app: Spotify                 # short form: fills the first option
      - click_image:                      # long form: named options
          image: images/search.png
          timeout: 15
        retries: 2                        # step options sit next to the action
      - type: "{{ song }}"

All checking happens here, before anything runs, so a typo is reported
immediately instead of halfway through moving your mouse around.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .actions import REGISTRY, matches_type, type_name
from .errors import WorkflowError

STEP_OPTIONS = {"name", "retries", "optional"}
TOP_LEVEL_KEYS = {"name", "description", "vars", "steps"}
VARIABLE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


@dataclass
class Step:
    index: int
    action: str
    params: dict[str, Any]
    name: str | None = None
    retries: int = 0
    optional: bool = False

    def describe(self) -> str:
        if self.name:
            return self.name
        shown = ", ".join(f"{k}={v!r}" for k, v in self.params.items())
        return f"{self.action}({shown})"


@dataclass
class Workflow:
    name: str
    steps: list[Step]
    description: str = ""
    variables: dict[str, str] = field(default_factory=dict)
    base_dir: Path = field(default_factory=Path.cwd)
    source: str = "<string>"

    def image_paths(self) -> list[Path]:
        return [self.base_dir / s.params["image"] for s in self.steps if "image" in s.params]

    def missing_images(self) -> list[Path]:
        return [p for p in self.image_paths() if not p.is_file()]


def builtin_variables() -> dict[str, str]:
    now = datetime.now()
    return {"today": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M")}


def load_workflow(path: str | Path, overrides: dict[str, str] | None = None) -> Workflow:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkflowError(f"cannot read file: {exc.strerror}", source=str(path)) from exc
    return parse_workflow(text, source=str(path), base_dir=path.parent, overrides=overrides)


def parse_workflow(
    text: str,
    *,
    source: str = "<string>",
    base_dir: Path | None = None,
    overrides: dict[str, str] | None = None,
) -> Workflow:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        hint = ""
        if "{{" in text and "unhashable" in str(exc):
            hint = '\nhint: put quotes around values that use variables, e.g. "{{ song }}"'
        raise WorkflowError(f"invalid YAML: {exc}{hint}", source=source) from exc

    if not isinstance(data, dict):
        raise WorkflowError("the file must be a mapping with at least `steps:`", source=source)
    unknown = set(data) - TOP_LEVEL_KEYS
    if unknown:
        keys = ", ".join(sorted(unknown))
        raise WorkflowError(f"unknown top-level key(s): {keys}", source=source)

    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise WorkflowError("`steps:` must be a non-empty list", source=source)

    variables = _collect_variables(data.get("vars"), overrides, source)
    steps = [
        _parse_step(raw, index, variables, source) for index, raw in enumerate(raw_steps, start=1)
    ]
    return Workflow(
        name=str(data.get("name") or Path(source).stem),
        description=str(data.get("description") or ""),
        steps=steps,
        variables=variables,
        base_dir=base_dir or Path.cwd(),
        source=source,
    )


def _collect_variables(
    declared: Any, overrides: dict[str, str] | None, source: str
) -> dict[str, str]:
    if declared is None:
        declared = {}
    if not isinstance(declared, dict):
        raise WorkflowError("`vars:` must be a mapping of name: value", source=source)
    variables = builtin_variables()
    variables.update({str(k): str(v) for k, v in declared.items()})
    variables.update(overrides or {})
    return variables


def render(value: Any, variables: dict[str, str], source: str, step: int) -> Any:
    """Replace {{ name }} placeholders, looking inside lists and mappings too."""
    if isinstance(value, str):

        def substitute(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in variables:
                raise WorkflowError(
                    f"unknown variable {{{{ {name} }}}} "
                    f"(declare it under `vars:` or pass --var {name}=...)",
                    source=source,
                    step=step,
                )
            return variables[name]

        return VARIABLE.sub(substitute, value)
    if isinstance(value, list):
        return [render(v, variables, source, step) for v in value]
    if isinstance(value, dict):
        return {k: render(v, variables, source, step) for k, v in value.items()}
    return value


def _parse_step(raw: Any, index: int, variables: dict[str, str], source: str) -> Step:
    def fail(message: str) -> WorkflowError:
        return WorkflowError(message, source=source, step=index)

    if isinstance(raw, str):
        raw = {raw: None}  # allow bare `- some_action` with no options
    if not isinstance(raw, dict):
        raise fail("each step must look like `- action: value`")

    action_keys = [k for k in raw if k not in STEP_OPTIONS]
    if len(action_keys) != 1:
        found = ", ".join(map(str, action_keys)) or "none"
        raise fail(f"expected exactly one action per step, found: {found}")
    action = str(action_keys[0])

    spec = REGISTRY.get(action)
    if spec is None:
        raise fail(f"unknown action {action!r}. {_suggest(action)}")

    value = render(raw[action], variables, source, index)
    if value is None:
        params: dict[str, Any] = {}
    elif isinstance(value, dict):
        params = dict(value)
    elif spec.primary is not None:
        params = {spec.primary: value}
    else:
        raise fail(f"{action} takes no options")

    unknown = set(params) - set(spec.params)
    if unknown:
        allowed = ", ".join(spec.params) or "none"
        raise fail(
            f"{action} got unknown option(s) {', '.join(sorted(unknown))}; allowed: {allowed}"
        )
    missing = [p for p in spec.required if p not in params]
    if missing:
        raise fail(f"{action} is missing required option(s): {', '.join(missing)}")
    for key, val in params.items():
        hint = spec.hints.get(key)
        if hint is not None and not matches_type(val, hint):
            raise fail(f"{action}.{key} should be {type_name(hint)}, got {val!r}")

    retries = raw.get("retries", 0)
    if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0:
        raise fail("`retries` must be a whole number >= 0")
    optional = raw.get("optional", False)
    if not isinstance(optional, bool):
        raise fail("`optional` must be true or false")
    name = raw.get("name")

    return Step(
        index=index,
        action=action,
        params=params,
        name=str(name) if name is not None else None,
        retries=retries,
        optional=optional,
    )


def _suggest(action: str) -> str:
    import difflib

    close = difflib.get_close_matches(action, REGISTRY, n=1)
    if close:
        return f"Did you mean {close[0]!r}?"
    return "Run `autoflow actions` to see them all."

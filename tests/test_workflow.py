from __future__ import annotations

from datetime import date

import pytest

from autoflow.errors import WorkflowError
from autoflow.workflow import load_workflow, parse_workflow


def test_short_and_long_step_forms():
    wf = parse_workflow("""
name: Demo
steps:
  - press: enter
  - click: { x: 10, y: 20, clicks: 2 }
  - hotkey: [command, space]
""")
    assert wf.name == "Demo"
    assert [s.action for s in wf.steps] == ["press", "click", "hotkey"]
    assert wf.steps[0].params == {"key": "enter"}
    assert wf.steps[1].params == {"x": 10, "y": 20, "clicks": 2}
    assert wf.steps[2].params == {"keys": ["command", "space"]}
    assert [s.index for s in wf.steps] == [1, 2, 3]


def test_step_options_are_separate_from_action_options():
    wf = parse_workflow("""
steps:
  - name: Find it
    click_image: { image: a.png }
    retries: 3
    optional: true
""")
    step = wf.steps[0]
    assert (step.name, step.retries, step.optional) == ("Find it", 3, True)
    assert step.describe() == "Find it"


def test_variables_defaults_overrides_and_builtins():
    text = """
vars: { song: Default }
steps:
  - type: "{{ song }} / {{today}}"
"""
    assert parse_workflow(text).steps[0].params["text"].startswith("Default / ")
    wf = parse_workflow(text, overrides={"song": "Other"})
    assert wf.steps[0].params["text"] == f"Other / {date.today():%Y-%m-%d}"


def test_name_defaults_to_file_name(tmp_path):
    path = tmp_path / "my_flow.yaml"
    path.write_text("steps: [{press: tab}]")
    wf = load_workflow(path)
    assert wf.name == "my_flow"
    assert wf.base_dir == tmp_path


def test_missing_images_are_resolved_relative_to_the_file(tmp_path):
    (tmp_path / "here.png").write_bytes(b"x")
    path = tmp_path / "flow.yaml"
    path.write_text("steps: [{click_image: here.png}, {wait_for_image: gone.png}]")
    assert load_workflow(path).missing_images() == [tmp_path / "gone.png"]







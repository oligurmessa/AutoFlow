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













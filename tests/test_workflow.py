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


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("steps: [{tpye: hi}]", "Did you mean 'type'?"),
        ("steps: [{click: {x: 1}}]", "missing required option(s): y"),
        ("steps: [{wait: soon}]", "wait.seconds should be float"),
        ("steps: [{press: {key: a, force: 2}}]", "unknown option(s) force"),
        ("steps: [{press: a, type: b}]", "exactly one action"),
        ("steps: [{press: a, retries: -1}]", "`retries` must be"),
        ("steps: [{type: '{{ nope }}'}]", "unknown variable {{ nope }}"),
        ("steps: [{type: {{ nope }}}]", "put quotes around values"),
        ("steps: []", "non-empty list"),
        ("name: x", "non-empty list"),
        ("stepz: [{press: a}]", "unknown top-level key(s): stepz"),
        ("- just a list", "must be a mapping"),
    ],
)
def test_invalid_workflows_explain_the_problem(text, message):
    with pytest.raises(WorkflowError) as err:
        parse_workflow(text, source="flow.yaml")
    assert message in str(err.value)
    assert str(err.value).startswith("flow.yaml")


def test_error_points_at_the_step_number():
    with pytest.raises(WorkflowError, match="step 3"):
        parse_workflow("steps: [{press: a}, {press: b}, {nope: c}]")


def test_unreadable_file(tmp_path):
    with pytest.raises(WorkflowError, match="cannot read file"):
        load_workflow(tmp_path / "missing.yaml")

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from autoflow.cli import EXIT_INVALID, EXIT_OK, main

FLOWS = Path(__file__).resolve().parent.parent / "flows"


@pytest.fixture(autouse=True)
def _capture_info_logs(caplog):
    caplog.set_level(logging.INFO, logger="autoflow")


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text)
    return path


def test_bundled_example_flows_are_valid():
    assert main(["validate", str(FLOWS)]) == EXIT_OK


def test_validate_reports_invalid_files(tmp_path, caplog):
    write(tmp_path, "good.yaml", "steps: [{press: enter}]")
    write(tmp_path, "bad.yml", "steps: [{prss: enter}]")
    assert main(["validate", str(tmp_path)]) == EXIT_INVALID
    assert "Did you mean 'press'?" in caplog.text
    assert "2 file(s) checked, 1 invalid" in caplog.text


def test_validate_with_no_files(tmp_path):
    assert main(["validate", str(tmp_path)]) == EXIT_INVALID


def test_dry_run_shows_rendered_steps(tmp_path, caplog):
    flow = write(
        tmp_path,
        "f.yaml",
        """
name: Greeting
vars: { who: World }
steps:
  - type: "Hello {{ who }}"
""",
    )
    assert main(["run", str(flow), "--dry-run", "--var", "who=Class"]) == EXIT_OK
    assert "type(text='Hello Class')" in caplog.text


def test_run_refuses_to_start_when_images_are_missing(tmp_path, caplog):
    flow = write(tmp_path, "f.yaml", "steps: [{click_image: missing.png}]")
    assert main(["run", str(flow), "--countdown", "0"]) == EXIT_INVALID
    assert "image not found" in caplog.text


def test_invalid_workflow_exit_code(tmp_path):
    flow = write(tmp_path, "f.yaml", "steps: [{type: '{{ nope }}'}]")
    assert main(["run", str(flow), "--dry-run"]) == EXIT_INVALID


def test_bad_var_syntax(tmp_path):
    flow = write(tmp_path, "f.yaml", "steps: [{press: a}]")
    with pytest.raises(SystemExit):
        main(["run", str(flow), "--var", "novalue"])


def test_actions_lists_everything(capsys):
    assert main(["actions"]) == EXIT_OK
    out = capsys.readouterr().out
    for name in ("click_image", "wait_for_image", "hotkey", "type", "open_app"):
        assert name in out

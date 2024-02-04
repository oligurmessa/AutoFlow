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











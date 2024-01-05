from __future__ import annotations

import pytest

from autoflow import actions
from autoflow.actions import REGISTRY, matches_type
from autoflow.errors import ImageNotFound, StepFailed


def test_every_action_has_a_summary():
    for spec in REGISTRY.values():
        assert spec.summary, f"{spec.name} needs a docstring"


def test_signature_shows_defaults():
    assert REGISTRY["press"].signature() == "press(key, times=1)"
    assert REGISTRY["click"].required == ["x", "y"]


@pytest.mark.parametrize(
    ("value", "hint", "ok"),
    [
        (2, float, True),
        (2.5, int, False),
        (True, int, False),
        ("a", str | list[str], True),
        (["a", "b"], str | list[str], True),
        (["a", 1], list[str], False),
        (None, float | None, True),
    ],
)
def test_matches_type(value, hint, ok):
    assert matches_type(value, hint) is ok















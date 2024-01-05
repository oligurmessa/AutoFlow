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


def test_hotkey_accepts_plus_string_or_list(ctx, backend):
    actions.hotkey(ctx, "Command + Space")
    actions.hotkey(ctx, ["ctrl", "shift", "t"])
    assert backend.calls == [
        ("hotkey", ("command", "space")),
        ("hotkey", ("ctrl", "shift", "t")),
    ]


def test_click_rejects_unknown_button(ctx):
    with pytest.raises(StepFailed, match="button must be"):
        actions.click(ctx, 1, 2, button="side")


def test_wait_for_image_polls_until_it_appears(ctx, backend, clock, image):
    backend.visible = {image: (50, 60)}
    backend.appear_after = {image: 3}
    assert actions.wait_for_image(ctx, image) == (50, 60)
    assert clock.sleeps == [0.5, 0.5, 0.5]


def test_wait_for_image_times_out(ctx, clock, image):
    with pytest.raises(ImageNotFound, match="did not appear within 2s"):
        actions.wait_for_image(ctx, image, timeout=2)
    assert clock.now == pytest.approx(2.0)


def test_wait_for_image_requires_the_file(ctx):
    with pytest.raises(StepFailed, match="image file not found"):
        actions.wait_for_image(ctx, "nope.png")


def test_click_image_clicks_centre_plus_offset(ctx, backend, image):
    backend.visible = {image: (100, 200)}
    actions.click_image(ctx, image, offset_x=5, offset_y=-10, clicks=2)
    assert backend.calls == [("click", (105, 190, 2, "left"))]


def test_open_app_waits_for_the_app(ctx, backend, clock):
    actions.open_app(ctx, "Notes", wait=1.5)
    assert backend.calls == [("open_app", "Notes")]
    assert clock.sleeps == [1.5]

from __future__ import annotations

from autoflow.actions import REGISTRY, action
from autoflow.runner import Runner
from autoflow.workflow import parse_workflow


def make_runner(ctx, tmp_path, **kwargs):
    return Runner(ctx, retry_delay=0.1, failure_dir=tmp_path / "failures", **kwargs)


def test_runs_every_step_in_order(ctx, backend, tmp_path):
    wf = parse_workflow("""
steps:
  - open_app: { app: Notes, wait: 0 }
  - type: hello
  - press: { key: tab, times: 2 }
""")
    result = make_runner(ctx, tmp_path).run(wf)
    assert result.ok
    assert backend.calls == [
        ("open_app", "Notes"),
        ("write", "hello"),
        ("press", ("tab", 2)),
    ]


def test_retry_succeeds_on_a_later_attempt(ctx, backend, image, tmp_path):
    backend.visible = {image: (1, 1)}
    backend.appear_after = {image: 2}
    wf = parse_workflow(f"steps: [{{click_image: {{image: {image}, timeout: 0}}, retries: 2}}]")
    result = make_runner(ctx, tmp_path).run(wf)
    assert result.ok
    assert result.results[0].attempts == 3


def test_failure_stops_the_run_and_takes_a_screenshot(ctx, backend, image, tmp_path):
    wf = parse_workflow(f"""
steps:
  - click_image: {{ image: {image}, timeout: 1 }}
  - type: never typed
""")
    result = make_runner(ctx, tmp_path).run(wf)
    assert not result.ok
    assert result.failed.step.index == 1
    assert "did not appear" in result.failed.error
    assert len(result.results) == 1
    assert result.screenshot is not None and result.screenshot.parent == tmp_path / "failures"
    assert ("write", "never typed") not in backend.calls


def test_optional_step_failure_is_skipped(ctx, backend, image, tmp_path):
    wf = parse_workflow(f"""
steps:
  - click_image: {{ image: {image}, timeout: 0 }}
    optional: true
  - type: still typed
""")
    result = make_runner(ctx, tmp_path).run(wf)
    assert result.ok
    assert result.results[0].skipped
    assert backend.calls[-1] == ("write", "still typed")





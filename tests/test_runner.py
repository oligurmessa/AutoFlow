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









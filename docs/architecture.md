# Architecture

AutoFlow is small, but it's split the way larger tools are. Each module has one job, and only one module talks to the real mouse and keyboard.

```
 flow.yaml
    │
    ▼
 workflow.py   load YAML → fill in {{ vars }} → check every step against the registry
    │           produces: Workflow(steps=[Step, Step, ...])
    ▼
 runner.py     for each step: call the action, retry on failure,
    │           screenshot + stop on a real failure, skip optional ones
    ▼
 actions.py    one function per step type, e.g. click_image(ctx, image, timeout)
    │           all actions get a Context (backend, base folder, clock)
    ▼
 backends.py   PyAutoGUIBackend  → pyautogui → your actual screen
               FakeBackend       → records calls (tests, --dry-run)
```

`cli.py` connects these for the terminal, and `platform.py` holds the OS-specific code for launching apps.

## Design decisions

### Why a Backend interface?
The original script called `pyautogui` directly. That made it impossible to test without a screen, and every test run moved your real mouse. Now actions only talk to a `Backend`. Tests use `FakeBackend`, which records what *would* have happened:

```python
backend = FakeBackend(visible={"button.png": (100, 200)})
click_image(ctx, "button.png")
assert backend.calls == [("click", (100, 200, 1, "left"))]
```

This idea is called *dependency injection*: the caller decides which implementation gets used.

### Why inject `sleep` and `clock`?
`wait_for_image` polls with a timeout. Testing a 10-second timeout with real time would make the test suite slow. `Context` takes `sleep` and `clock` functions, and tests pass a `FakeClock` that jumps forward instantly. The whole suite runs in well under a second.

### Why validate before running?
When a workflow fails halfway through, your screen is left in a random state. `workflow.py` catches everything it can up front: unknown actions (with "did you mean" suggestions), missing or unknown options, wrong types, undefined variables and missing image files.

### Why a decorator registry?
Each action declares its options through its normal Python signature:

```python
@action("press")
def press(ctx: Context, key: str, times: int = 1) -> None:
    """Press a single key such as enter, tab, esc, up or f5."""
```

From that one function, AutoFlow gets:
- the option names and which ones are required (`inspect.signature`)
- the types to validate against (`typing.get_type_hints`)
- the help text for `autoflow actions` (the docstring)
- the short form (`- press: enter` fills the first option)

## Walkthrough: adding a new action

Say you want a `copy_text` action that puts text on the clipboard.

1. **Backend.** Add `copy(self, text: str) -> None` to the `Backend` protocol. Implement it in `PyAutoGUIBackend` (for example with the `pyperclip` package) and in `FakeBackend` (append to `self.calls`).
2. **Action.** In `actions.py`:
   ```python
   @action("copy_text")
   def copy_text(ctx: Context, text: str) -> None:
       """Put text on the clipboard."""
       ctx.backend.copy(text)
   ```
3. **Test.** In `tests/test_actions.py`:
   ```python
   def test_copy_text(ctx, backend):
       actions.copy_text(ctx, "hi")
       assert backend.calls == [("copy", "hi")]
   ```
4. Run `pytest`, then try `- copy_text: "{{ today }}"` in a workflow with `--dry-run`.

Validation, `autoflow actions` and the short form all work automatically.

## Error handling

| Exception | Meaning | CLI exit code |
|-----------|---------|---------------|
| `WorkflowError` | the file is wrong; fix it and rerun | 2 |
| `StepFailed` / `ImageNotFound` | the file is fine, but the screen didn't cooperate | 1 |
| pyautogui `FailSafeException` | the user moved the mouse to a corner; never retried | 1 |

All of them inherit from `AutoflowError`, so the CLI can print one clean line instead of a traceback. Unexpected exceptions inside an action are caught by the runner and reported as a failed step.

## Ideas to practise with

- A `--screenshot-dir` CLI option for failure screenshots
- `if_image:` for conditional steps (hint: a step whose options include a nested list of steps)
- `run_workflow: other.yaml` to reuse workflows (watch out for infinite recursion!)
- A `--report run.json` option that writes each step's result and timing

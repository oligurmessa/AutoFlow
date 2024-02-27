# Writing workflows

A workflow is a YAML file with a list of steps. AutoFlow runs them from top to bottom.

```yaml
name: Rename screenshots        # optional; defaults to the file name
description: What this does     # optional
vars:                           # optional; use as {{ name }}
  folder: Desktop
steps:
  - open_app: Finder
  - hotkey: command+shift+g
  - type: "~/{{ folder }}"
  - press: enter
```

Run `autoflow validate path/to/file.yaml` after every edit. It's instant and it doesn't touch your screen.

## Step syntax

Each step has **exactly one action**. There are two ways to write it:

```yaml
- press: enter                    # short form: the value fills the first option

- press:                          # long form: name every option
    key: tab
    times: 3
```

**Step options** go *next to* the action, not inside it:

```yaml
- name: Click the search box      # a friendly label for the log
  click_image: images/search.png
  retries: 2                      # try again up to 2 more times if it fails
  optional: true                  # if it still fails, continue anyway
```

## Actions

Run `autoflow actions` for the full, up-to-date list.

| Action | Short form | Options |
|--------|-----------|---------|
| `open_app` | `open_app: Spotify` | `app`, `wait` (seconds, default 2) |
| `open_url` | `open_url: https://...` | `url` |
| `type` | `type: hello` | `text`, `interval` (seconds between keys) |
| `press` | `press: enter` | `key`, `times` |
| `hotkey` | `hotkey: command+c` | `keys`, written as `"a+b"` or `[a, b]` |
| `click` | *(long form only)* | `x`, `y`, `clicks`, `button` (`left`/`right`/`middle`) |
| `move_to` | *(long form only)* | `x`, `y` |
| `scroll` | `scroll: -5` | `amount` (positive = up) |
| `wait_for_image` | `wait_for_image: images/x.png` | `image`, `timeout`, `confidence` |
| `click_image` | `click_image: images/x.png` | `image`, `timeout`, `confidence`, `clicks`, `offset_x`, `offset_y` |
| `screenshot` | `screenshot: shots/now.png` | `path` |
| `wait` | `wait: 1.5` | `seconds` |
| `log` | `log: Done!` | `message` |

Key names follow [pyautogui's list](https://pyautogui.readthedocs.io/en/latest/keyboard.html#keyboard-keys): `enter`, `tab`, `esc`, `space`, `backspace`, `up`, `down`, `f1`…`f12`, `command`, `ctrl`, `alt`, `shift`, and so on.

## Variables

```yaml
vars:
  song: My 1st Song
steps:
  - type: "{{ song }}"          # quotes are required around {{ }}
```

- Override from the command line: `autoflow run flow.yaml --var song="Other Song"`.
- Built-in variables: `{{ today }}` (`2024-01-31`) and `{{ time }}` (`14:05`).
- Using a variable that doesn't exist is an error, caught by `validate`.

> **Why the quotes?** In YAML, `{ ... }` means "mapping", so `type: {{ song }}` is read as a strange nested mapping. AutoFlow notices this mistake and tells you how to fix it.

## Capturing images

`click_image` and `wait_for_image` look for a small screenshot snippet on your screen.

1. Get the app into the state you want to automate.
2. Take a snippet of the button:
   - macOS: `Cmd+Shift+4`, then drag
   - Windows: `Win+Shift+S`
3. Crop it **tightly** around something unique, like an icon plus a bit of its label. Leave out the background and anything that changes (counters, cursors).
4. Save it next to the workflow, for example `flows/images/spotify_search.png`, and refer to it with a path **relative to the workflow file**.

If a match fails:
- Run with `-v` and look at the failure screenshot in `autoflow-failures/`.
- Lower `confidence` a little (0.7), or crop the snippet more tightly.
- Take the snippet on the same screen, with the same theme (dark/light) and zoom as when you run the workflow.

## Tips for reliable workflows

- **Wait for things, not for time.** Use `wait_for_image` instead of `wait: 5`. It continues as soon as the button appears, and gives a clear error if it never does.
- **Prefer keyboard shortcuts** over clicking coordinates. Coordinates break when a window moves.
- **Use `--dry-run`** to check the order of steps and the variable values.
- **Keep an escape route:** moving the mouse into any screen corner stops the run immediately.

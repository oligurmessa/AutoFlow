# AutoFlow

**Automate repetitive desktop tasks by writing simple YAML workflows.**

AutoFlow controls your mouse and keyboard for you. It can open apps, type text, press shortcuts, and find and click buttons on screen by matching screenshots. You describe the steps once in a readable file and replay them whenever you like.

```yaml
# flows/play_song.yaml
name: Play a song on Spotify
vars:
  song: My 1st Song
steps:
  - open_app: Spotify
  - click_image: { image: images/spotify_search.png, timeout: 20 }
  - type: "{{ song }}"
  - press: enter
```

```console
$ autoflow run flows/play_song.yaml --var song="Clair de Lune"
Starting in 3s - move the mouse into a screen corner to abort.
▶ Play a song on Spotify (4 steps)
  [1/4] open_app(app='Spotify')
  [2/4] click_image(image='images/spotify_search.png', timeout=20)
  [3/4] type(text='Clair de Lune')
  [4/4] press(key='enter')
✔ finished Play a song on Spotify
```

## Features

- **Readable workflows.** Plain YAML, with `{{ variables }}` you can override from the command line.
- **Waits instead of guessing.** `wait_for_image` / `click_image` check the screen repeatedly until a button appears, instead of relying on a fixed `sleep(5)`.
- **Checks before running.** Typos, missing options, wrong types and missing screenshots are reported *before* the mouse moves, with suggestions (`unknown action 'tpye'. Did you mean 'type'?`).
- **Recovers from flaky steps.** Per-step `retries`, `optional` steps, and an automatic screenshot when a step fails.
- **Safe to try.** `--dry-run` prints what would happen, there's a start countdown, and moving the mouse into a screen corner aborts at any time.
- **Cross-platform.** macOS, Windows and Linux. Apps open through the OS itself, not through simulated Spotlight keystrokes. Retina screens are handled.
- **Tested.** 49 tests run against a fake backend, so they need no screen, and CI runs them on all three operating systems.

## Install

Requires Python 3.10+.

```bash
git clone <this repo> autoflow
cd autoflow
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

**macOS:** give your terminal app access under **System Settings → Privacy & Security → Accessibility** (to control the mouse and keyboard) and **Screen Recording** (to find images). Otherwise clicks and image matching fail without any error message.

## Usage

```bash
autoflow actions                              # list every step type
autoflow validate flows/                      # check workflow files without running them
autoflow run flows/morning_tabs.yaml          # run one
autoflow run flows/daily_note.yaml --dry-run  # show the steps, touch nothing
autoflow run flows/play_song.yaml --var song="Bohemian Rhapsody" --timeout 20
```

| Option | Meaning |
|--------|---------|
| `--var NAME=VALUE` | Set a workflow variable (repeatable) |
| `--dry-run` | Print the steps without doing them |
| `--countdown S` | Seconds to wait before starting (default 3) |
| `--timeout S` | Default wait for images (default 10) |
| `--confidence C` | Default image-match strictness, 0–1 (default 0.8) |
| `-v` | Debug output (timings, retries) |

Exit codes: `0` success, `1` a step failed, `2` the workflow is invalid.

## Example workflows

| File | What it does | Needs a screenshot? |
|------|--------------|---------------------|
| [`flows/morning_tabs.yaml`](flows/morning_tabs.yaml) | Opens the web pages you check every morning | No |
| [`flows/daily_note.yaml`](flows/daily_note.yaml) | Starts a dated note in TextEdit (macOS) | No |
| [`flows/play_song.yaml`](flows/play_song.yaml) | Searches Spotify for a song | Yes: capture `flows/images/spotify_search.png` |

To write your own, read [docs/writing-workflows.md](docs/writing-workflows.md).


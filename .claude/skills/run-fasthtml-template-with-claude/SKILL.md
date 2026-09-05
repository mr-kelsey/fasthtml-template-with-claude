---
name: run-fasthtml-template-with-claude
description: Build, run, and drive the FastHTML family calendar app (this repo). Use when asked to start the app, run its tests, or take a screenshot of the calendar/notes UI, or interact with the running server.
---

A server-rendered FastHTML + SQLite web app (family calendar + notes) on `http://localhost:5001`. Drive it by starting the dev server, then running the Playwright driver at `.claude/skills/run-fasthtml-template-with-claude/driver.py`, which clicks through the calendar UI and screenshots each step. All paths below are relative to the repo root.

## Prerequisites

No extra `apt-get` packages were needed in this container — Playwright's bundled Chromium download and launch (with `--no-sandbox`) worked out of the box.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # pytest + playwright
playwright install chromium           # one-time browser download, ~185MB
```

The app reads two gitignored config files that must exist:

```bash
cp family.example.json family.json   # if you don't have real family data
```

`.env` (SQLite path, port) is expected to already exist at repo root with `PORT=5001` and `DB_PATH=data/app.db` — copy from a `.env.example` or create it if missing.

## Build

No build step — pure Python, server-rendered HTML.

## Run (agent path)

Start the dev server in the background and wait for it to actually serve, then run the driver:

```bash
source .venv/bin/activate
(python main.py > /tmp/fasthtml-server.log 2>&1 &)
timeout 30 bash -c 'until curl -sf http://localhost:5001 >/dev/null; do sleep 1; done'

python .claude/skills/run-fasthtml-template-with-claude/driver.py
```

The driver: opens `/calendar`, clicks "Person 1" in the filter row (which doubles as the member picker — this sets `member_id` in the session), screenshots the month grid, clicks today's day square, screenshots the opened `<dialog>` modal, fills and submits the add-event form with a critical event titled "Driver Smoke Test", screenshots the grid again, prints the count of `.event-bar` and `.day-square.critical-day` elements plus any browser console errors, then **deletes the event it just created** via `db.delete_event` so the real dev database (`data/app.db`) is left exactly as it found it.

Screenshots land in `.claude/skills/run-fasthtml-template-with-claude/screenshots/` (`01-grid.png`, `02-dialog.png`, `03-after-add.png`).

Stop the server when done:

```bash
lsof -ti:5001 -sTCP:LISTEN | xargs -r kill
```

## Run (human path)

```bash
source .venv/bin/activate
python main.py           # -> http://localhost:5001, autoreload. Ctrl-C to stop.
```

or

```bash
docker compose up --build   # -> http://localhost:5001
```

## Test

```bash
source .venv/bin/activate
pytest -q
```

All tests should pass. Tests use `.env.test` (a separate DB truncated per-test), never `data/app.db` — safe to run anytime, no server needs to be running.

---

## Gotchas

- **`db.py` resolves `.env`/`family.json` relative to the current working directory**, not to the script's location — always run `driver.py` (and `main.py`) from the repo root, or `db.Database()` silently falls back to `data/app.db` under whatever directory you happened to be in.
- **The driver mutates the real dev database** (adds then deletes one event by exact title match `"Driver Smoke Test"`). If the driver is killed mid-run (e.g. Ctrl-C between add and cleanup), an orphan event survives — check with `python -c "import db; [print(dict(e)) for e in db.list_events()]"` and remove it manually with `db.delete_event(<id>)`.
- **A fresh browser context has no session cookie**, so `GET /calendar` renders the grid unfiltered ("Everyone") with no `member_id` in the session — the driver clicks "Person 1" in the filter row before adding an event. Skipping that step causes the add-event POST to fail with 422 ("Pick a family member from the filter before adding events.") since `pages/calendar.py`'s `add_event_route` requires `sess["member_id"]`.

## Troubleshooting

- **`ModuleNotFoundError: No module named 'playwright'`**: not installed in the active venv. `pip install -r requirements-dev.txt`.
- **`playwright._impl._errors.TimeoutError: ... waiting for locator(".filter-row a:has-text('Person 1')")`**: `family.json` doesn't exist and the placeholder fallback wasn't loaded, or a custom `family.json` has different member names — check `family.py`'s `FAMILY_MEMBERS` and adjust the driver's click target to match a real name.
- **Add-event POST returns 422 "Pick a family member from the filter before adding events."**: the driver skipped or failed the filter-row click, so `sess["member_id"]` was never set — see Gotchas.

# CLAUDE.md

## Project Overview

FastHTML multipage app with SQLite persistence via SQLAlchemy Core (`text()` queries, no ORM). Docker-ready.

## Commands

Without Docker:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py           # dev server with autoreload
```

With Docker Compose:
```bash
docker compose up --build   # -> http://localhost:5001
```

Tests (no external services needed):
```bash
pip install -r requirements-dev.txt
pytest                                              # full suite
pytest tests/test_db.py::test_add_and_list_note     # single test
```
Uses `.env.test` (not `.env`) via `db.Database(".env.test")`, swapped in by `tests/conftest.py` before `main`/pages are imported — truncates `notes`/`calendar_events` in its own db, never the real one configured in `.env`.

## Architecture

- `main.py` — builds the app, registers `init_db` as a startup hook, mounts every page module's router (`page.router.to_app(app)`). Page modules are auto-discovered via `pages.discover_page_modules()` — no manual registration needed.
- `pages/__init__.py` — `discover_page_modules()` walks `pages/*.py` and returns every module that defines a `router` attribute (alphabetical order, submodules only, packages skipped).
- `pages/*.py` — one module per route group, each owns `router = fast.APIRouter()`. `notes.py` is the full CRUD reference (list/add/delete against SQLite).
- `layout.py` — shared `layout(title, *content)` wrapper; `NAV_LINKS` drives the nav bar.
- `family.py` — loads `FAMILY_MEMBERS` (id/name/color) from `family.json` if present, else falls back to generic placeholders. `family.json` is a real, gitignored config file (like `.env`) holding the user's actual family member names — it is expected to exist and **must not** be hardcoded into `family.py` or any tracked file; `family.example.json` is only the checked-in template.
- `db.py` — `Database(env_file=".env")` class owns one SQLAlchemy `engine` (`sqlite:///{DB_PATH}`) and all queries (`text()` + bound `:params`); `connect_args={"check_same_thread": False}` is required since Starlette runs sync handlers in a thread pool. A module-level `_instance` (default `Database()`) is what `db.list_notes()`, `db.engine`, etc. actually resolve to, via a module `__getattr__` — this lets `tests/conftest.py` swap `db._instance` to a `Database(".env.test")` before `main`/pages import, with zero changes needed in the callers (they always go through `db.<name>`, never bind it early).
- New page: create `pages/foo.py` with its own `router` — it's picked up automatically on next run/import. Optionally link it in `layout.py`'s `NAV_LINKS`.

## Conventions

- Class names: `Titled_Snake_Case`.
- FastHTML docs: https://www.fastht.ml/docs/llms-ctx.txt

# CLAUDE.md

## Project Overview

FastHTML multipage app with SQLite persistence via SQLAlchemy Core (`text()` queries, no ORM). Docker-ready.

## Commands

Without Docker:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit DB_PATH if you don't want data/app.db
python main.py           # dev server with autoreload
```

With Docker Compose:
```bash
cp .env.example .env && docker compose up --build   # -> http://localhost:5001
```

Tests (no external services needed):
```bash
pip install -r requirements-dev.txt
pytest                                              # full suite
pytest tests/test_db.py::test_add_and_list_note     # single test
```
Truncates `notes` before/after every test (`tests/conftest.py`) — set `DB_PATH` to a separate file for isolation.

## Architecture

- `main.py` — builds the app, registers `init_db` as a startup hook, mounts every page module's router (`page.router.to_app(app)`). Page modules are auto-discovered via `pages.discover_page_modules()` — no manual registration needed.
- `pages/__init__.py` — `discover_page_modules()` walks `pages/*.py` and returns every module that defines a `router` attribute (alphabetical order, submodules only, packages skipped).
- `pages/*.py` — one module per route group, each owns `router = fast.APIRouter()`. `notes.py` is the full CRUD reference (list/add/delete against SQLite).
- `layout.py` — shared `layout(title, *content)` wrapper; `NAV_LINKS` drives the nav bar.
- `db.py` — single SQLAlchemy `engine` (`sqlite:///{DB_PATH}`), raw `SCHEMA_SQL` DDL run by `init_db()`, queries via `text()` + bound `:params`. `connect_args={"check_same_thread": False}` is required — Starlette runs sync handlers in a thread pool, and a pooled sqlite3 connection can otherwise get reused from a different thread than the one that created it.
- New page: create `pages/foo.py` with its own `router` — it's picked up automatically on next run/import. Optionally link it in `layout.py`'s `NAV_LINKS`.

## Conventions

- Class names: `Titled_Snake_Case`.
- FastHTML docs: https://www.fastht.ml/docs/llms-ctx.txt

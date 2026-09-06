# CLAUDE.md

## Project Overview

A suite of family productivity applications accessible to each family member from within the LAN.  Branch focus: farm planning.

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

## Farm Planning Plan

Goal: plan crops/beds on the newly-purchased land, track germination timing for succession planting, and log weather/precipitation.

- **Farm calendar is separate from the family calendar** — its own `farm_events` table and `pages/farm_calendar.py`/router, own nav link, not stored in `calendar_events`. Reason: farm events need fields family events don't (`linked_planting_id`, event type like germination-check/harvest/frost-warning), and family event coloring is keyed to `FAMILY_MEMBERS` which doesn't fit farm events. Extract the reusable month-grid/day-square/dialog rendering out of `pages/calendar.py` into a shared helper both calendars call, rather than duplicating it.
- **Done — plant/variety/planting data layer**: `plants` (the crop, e.g. "Tomato" — carries *default* agronomic data: species, plant_family, germination_days_min/max, days_to_maturity_min/max, spacing_in, sun/water needs) → `seed_varieties` (the specific cultivar, `plant_id` + name required, same agronomic columns as nullable **overrides** resolved via `COALESCE(variety.x, plant.x)` at query time — `db.list_seed_varieties()`/`db.list_plantings()` return the effective values) → `plantings` (`variety_id`, `bed_id` nullable/unused until `beds` exists, `location` free text, `planted_date`, quantity/quantity_germinated, notes). Pages: `pages/plants.py`, `pages/seed_varieties.py`, `pages/plantings.py`, all list/add/edit/delete; shared parsing/formatting helpers live in `farm.py` (sibling to `family.py`/`layout.py`/`db.py`).
- **Done — succession-overlap warning**: `pages/plantings.py`'s `_overlap_warnings()` groups plantings by non-blank `location` and flags pairs whose expected harvest windows (`planted_date` + effective `days_to_maturity`) intersect — pulled forward ahead of the bed/map view since it doesn't need real bed geometry, just a free-text location match.
- **Next — interactive land map**: SVG-based (not canvas), drag/resize beds via a lightweight JS lib (e.g. interact.js via CDN) or hand-rolled pointer events, htmx POST of updated `shape` JSON on drop — same round-trip pattern as existing calendar htmx dialogs. Beds can exist unpositioned (staging) since layout isn't locked in yet. Once `beds` exists, `plantings.bed_id` should take over from the free-text `location` field for overlap detection.
- **Then — bed detail view** (`/beds/{id}`): grid of rows/zones sized from bed dimensions and variety spacing; adding a planting here auto-generates linked farm-calendar events (germination check, expected harvest) computed from `planted_date + variety data` — not stored as separate state.
- **Deferred/overlooked items to revisit**: weather/precipitation API ingestion, frost-date-based planting validation, crop rotation history by plant family, companion/antagonist planting warnings, seed inventory + observed germination rate over time, harvest/yield log, mobile-friendly bed entry, printable/exportable seasonal planting calendar, task list (harden off seedlings, thin rows, start indoors) generated from planting dates, photo attachment per bed, multi-year bed history view for rotation planning.

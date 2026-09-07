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
pytest tests/test_db.py::test_add_note_persists_title_and_body     # single test
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
- **Done — seed variety/planting data layer**: originally split into `plants` (defaults) → `seed_varieties` (overrides via `COALESCE`), but that assumed taxonomic/common-name grouping predicts agronomic timing, which it doesn't (e.g. "Pepper" spans multiple actual species with different germination/maturity) — collapsed to one flat `seed_varieties` table instead: `common_name` (e.g. "Tomato") + `name` (the cultivar, e.g. "Cherokee Purple") both required, `plant_family` required, `genus`/`species` optional, agronomic fields (germination_days_min/max, days_to_maturity_min/max, spacing_in, sun/water needs) as plain per-row values — no overrides/inheritance. `plantings` (`variety_id`, `bed_id` nullable/unused until `beds` exists, `location` free text, `planted_date`, quantity/quantity_germinated, notes) references it. Pages: `pages/seed_varieties.py`, `pages/plantings.py`, both list/add/edit/delete; shared parsing/formatting helpers live in `farm.py` (sibling to `family.py`/`layout.py`/`db.py`).
- **Done — duplicate-variety convenience**: `GET /seed-varieties/{id}/duplicate` (`duplicate_seed_variety_page` in `pages/seed_varieties.py`) prefills the add form from an existing variety but posts to the create route, not update — the practical fix for repetitive agronomic-data entry across varieties of the same common name, chosen instead of resurrecting a parent/override table.
- **Done — succession-overlap warning**: `pages/plantings.py`'s `_overlap_warnings()` groups plantings by non-blank `location` and flags pairs whose expected harvest windows (`planted_date` + `days_to_maturity`, straight from the variety row) intersect — pulled forward ahead of the bed/map view since it doesn't need real bed geometry, just a free-text location match.
- **Done — interactive land map**: `land_plots` (name, width_ft/height_ft, whole-foot integers) → `beds` (plot_id, label, x/y nullable = unplaced, width_ft/height_ft, rotation_deg default 0, sun_exposure, irrigation_zone). Both CRUD'd from one module, `pages/land_plots.py` (mirrors `pages/calendar.py` bundling related sub-resources rather than fragmenting into more files). The map itself is `GET /land-plots/{id}/map`: SVG (`fasthtml.svg`'s `Svg`/`Rect`/`G`/`Text` — note these aren't in `fasthtml.common`, they need their own import) with `viewBox` sized to the plot's feet, one `G` per placed bed. `static/land-map.js` (new — first custom JS in the app; everything else is server-rendered + htmx) does hand-rolled pointer-event drag (whole-bed body) and resize (small corner-handle `Rect`), both snapping to whole feet and persisting via `fetch()` POST to `/beds/{id}/position` / `/beds/{id}/size` (204, no reload — the JS already applied the move/resize optimistically). Rotation is a plain number input in the edit dialog, not freehand drag. Unplaced beds (`x`/`y` NULL) show in a sidebar list with a plain-form "Add to map" button hitting `POST /beds/{id}/place` (sets 0,0) — deliberately not real cross-container HTML5 drag-and-drop. Clicking (not dragging) a bed opens an edit/delete dialog via the same `hx-get`-into-`<dialog>` idiom as the calendar's day-square; the JS distinguishes click from drag by pointer-movement distance and swallows the synthetic post-drag click in the capture phase so htmx's click trigger doesn't also fire. Verified live with a Playwright script (drag persists, click-after-drag does *not* reopen the dialog, genuine click does) since this repo has no other browser-interaction test coverage for JS.
- **Next — bed detail view** (`/beds/{id}`): grid of rows/zones sized from bed dimensions and variety spacing; adding a planting here auto-generates linked farm-calendar events (germination check, expected harvest) computed from `planted_date + variety data` — not stored as separate state. This is also where `plantings.bed_id` should finally get wired up (still unused/nullable today — `plantings.location` free text is what overlap-warning matching uses until this lands).
- **Deferred/overlooked items to revisit**: weather/precipitation API ingestion, frost-date-based planting validation, crop rotation history by plant family, companion/antagonist planting warnings, seed inventory + observed germination rate over time, harvest/yield log, mobile-friendly bed entry, printable/exportable seasonal planting calendar, task list (harden off seedlings, thin rows, start indoors) generated from planting dates, photo attachment per bed, multi-year bed history view for rotation planning, bed resize-handle hit target may be too small on large plots (handle is a flat 1ft square regardless of zoom).

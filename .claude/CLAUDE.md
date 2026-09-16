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
pytest tests/test_db.py::test_add_note_persists_title_and_body     # single core test
pytest tests/farm/                                  # farm subdomain's suite standalone
```
Uses `.env.test` (not `.env`) via `db.Database(".env.test")`, swapped in by `tests/conftest.py` before `main`/pages are imported — truncates every table in its own db (never the real one configured in `.env`), core tables via `tests/conftest.py`'s fixtures and farm tables via `tests/farm/conftest.py`'s (pytest merges both automatically for anything under `tests/farm/`). `tests/__init__.py`/`tests/farm/__init__.py` exist so pytest's default import mode can tell `tests.test_db`/`tests.test_routes` apart from `tests.farm.test_db`/`tests.farm.test_routes`.

`tests/farm/test_land_map_js.py`/`test_bed_detail_js.py` drive the hand-rolled `static/land-map.js`/`bed-detail.js` for real, via Playwright against a live `main.app` (`tests/farm/conftest.py`'s `live_server_url`/`browser`/`page` fixtures — a real `uvicorn.Server` in a background thread, sharing the same `.env.test` engine, so the existing per-test cleanup fixtures still apply). Needs `playwright install chromium` once if not already installed.

## Architecture

The app is split into subdomains, each free to grow its own pages/db/tests: **core** (notes, family calendar — at the repo root) and **farm** (`farm/`). A subdomain only makes sense as a split when its tables never join across the boundary — farm's tables only ever join each other, never `notes`/`calendar_events`, which is what makes the split clean rather than arbitrary. New unrelated feature areas (e.g. a future finance or chores subdomain) should follow the same `<name>/{db.py,pages/}` shape rather than growing inside `pages/` or `db.py`.

- `main.py` — builds the app, registers `init_db` as a startup hook, mounts every page module's router (`page.router.to_app(app)`) from **both** `pages.discover_page_modules()` and `farm.pages.discover_page_modules()` — no manual registration needed within either package.
- `router_discovery.py` — `discover_router_modules(package)`, the generic `iter_modules` walk (alphabetical order, submodules only, packages skipped) shared by `pages/__init__.py` and `farm/pages/__init__.py` so it isn't duplicated per subdomain. Each package still exposes its own no-arg `discover_page_modules()` calling into this with its own package.
- `pages/*.py` — one module per **core** route group (home, about, notes, calendar), each owns `router = fast.APIRouter()`. `notes.py` is the full CRUD reference (list/add/delete against SQLite).
- `farm/` — the farm-planning subdomain (see Farm Planning Plan below for what's in it):
  - `farm/db.py` — `FarmDatabaseMixin` holds farm's schema statements (`seed_varieties`/`plantings`/`land_plots`/`beds`/`farm_events`) and every farm query method. It's a pure mixin (relies on `self.engine`, never instantiates `Database` itself) composed onto the shared engine/instance in root `db.py` — see below.
  - `farm/helpers.py` — parsing/formatting helpers (`parse_agronomic_fields`, `compute_window`, etc.) for the farm pages, sibling to `family.py`/`layout.py`.
  - `farm/pages/*.py` — `farm_calendar.py`, `seed_varieties.py`, `plantings.py`, `land_plots.py`, each owning `router = fast.APIRouter()` like core pages do.
- `layout.py` — shared `layout(title, *content)` wrapper; `NAV_LINKS` drives the nav bar. Used by both core and farm pages.
- `calendar_shared.py` — presentation-generic month-grid/day-square/nav rendering (`month_grid`, `events_by_date`, `month_nav`, `day_square`, `calendar_grid`), no family/member concepts. Shared by `pages/calendar.py` (family calendar) and `farm/pages/farm_calendar.py` (farm calendar) so the two don't duplicate month-grid rendering; each page builds its own day "badges" (event bars) and hands them in. `day_square`'s `critical` flag is a generic "this day needs to visually stand out" capability (renders the `critical-day` CSS class) shared by both calendars — the family calendar's `calendar_events.is_critical` and the farm calendar's `frost-cover` events both set it, rather than each subdomain inventing its own highlighting. Lives at the root since both subdomains depend on it, not owned by either.
- `family.py` — loads `FAMILY_MEMBERS` (id/name/color) from `family.json` if present, else falls back to generic placeholders. `family.json` is a real, gitignored config file (like `.env`) holding the user's actual family member names — it is expected to exist and **must not** be hardcoded into `family.py` or any tracked file; `family.example.json` is only the checked-in template.
- `db.py` — `_CoreDatabase` class owns one SQLAlchemy `engine` (`sqlite:///{DB_PATH}`), `init_db`, and the core (notes/calendar_events/recurring_events) schema/queries (`text()` + bound `:params`); `connect_args={"check_same_thread": False}` is required since Starlette runs sync handlers in a thread pool. The concrete `Database(FarmDatabaseMixin, _CoreDatabase)` class, defined at the bottom of this file, composes farm's schema/queries in via multiple inheritance and concatenates both `SCHEMA_STATEMENTS` lists so one `init_db()` call creates every table. A module-level `_instance` (default `Database()`) is what `db.list_notes()`, `db.add_planting()`, `db.engine`, etc. actually resolve to, via a module `__getattr__` — this lets `tests/conftest.py` swap `db._instance` to a `Database(".env.test")` before `main`/pages import, with zero changes needed in the callers (they always go through `db.<name>`, never bind it early). Callers never need to know or care that a method came from the core class vs. the farm mixin.
- New core page: create `pages/foo.py` with its own `router` — it's picked up automatically on next run/import. New farm page: same, but under `farm/pages/foo.py`. Optionally link it in `layout.py`'s `NAV_LINKS`.

## Conventions

- Class names: `Titled_Snake_Case`.
- FastHTML docs: https://www.fastht.ml/docs/llms-ctx.txt

## Farm Planning Plan

Goal: plan crops/beds on the newly-purchased land, track germination timing for succession planting, log weather/precipitation, and — the driving long-term goal — a **yield-prediction initiative**: collect enough structured per-planting data (genetics, soil, feeding, siting, weather, timing, actual yield) to eventually train a model predicting harvest weight (lb) from growing conditions.

**Status: phases 0–10 complete** (see git history for full per-phase design rationale — each commit/phase weighed and rejected at least one simpler alternative on domain-modeling grounds, worth reading before revisiting that area). Implemented data model and features:

- **Schema evolution**: no migration framework; `db.py`'s `SCHEMA_STATEMENTS` mixes plain `CREATE TABLE IF NOT EXISTS` strings with `(table, column, coldef)` tuples, the latter applied idempotently via `add_column_if_not_exists` (checks `PRAGMA table_info` since SQLite's `ALTER TABLE ADD COLUMN` has no `IF NOT EXISTS`).
- **`seed_varieties`**: flat, no taxonomic inheritance; carries `soil_type`/`soil_ph_min`/`soil_ph_max`, numeric `feeding_npk_n/p/k` + `feeding_frequency_days`, ordinal `sun_needs` (`full_sun`/`partial_shade`/`full_shade`, minimum light tolerated), `color_hex` (palette-assigned, used for map/lattice dots), and optional reference photos. `companion_rules` (companion/antagonist) keyed by common name, not variety, since folklore is crop-level.
- **Inventory**: `seed_lots`/`transplant_lots` (`farm/pages/inventory.py`) track physical stock separately from variety catalog data — seed age/quantity is a lot property, not a variety property. Direct-sow gating admits a lot with untracked (`NULL`, since the field is optional) or positive quantity, excluding one explicitly recorded as exhausted (`quantity_on_hand = 0`); transplant gating is an exact hard cap (`quantity_on_hand > 0`, no NULL allowance, since transplants are individually countable). `transplant_lots.origin_planting_id` / `purchased_*` carries provenance at the lot level (a whole tray shares one origin), not per-planting.
- **Plantings**: continuous inch-resolution `x_in`/`y_in` position (not the 12" visual grid, which is now display-only) is the sole authoritative placement, needed for correct real-distance spacing math. `source_type` (`seed`/`transplant`), `seed_lot_id`/`transplant_lot_id` FKs, `soil_temp_f` per-planting, `quantity_germinated`/`quantity_culled` (living count = germinated − culled).
- **Bed-planting flow** (`static/bed-detail.js`): variety-first lattice stamping — arm a variety, click spacing-interval lattice points to stage, submit a batch. Client-side spacing guard (true Euclidean distance, same-variety only, one bed at a time), companion/antagonist tinting, transplant-lot quantity gating with inline on-hand correction, seed-lot decrement (oldest-acquired-first) on submit.
- **Land map** (`static/land-map.js`): drag/resize beds on `land_plots`, plus shade: `shade_sources`/`shade_polygons` (freehand, full/partial × summer/winter, JSON point arrays) and `farm/geometry.py` (point-in-polygon, signed distance, continuous season-weighted blend between solstice extents) driving `classify_bed_cell_shade` — shown as a bed-grid tint and as a planting-time sun/shade warning.
- **Farm calendar / events**: `farm_events` grouped flat by `(variety_id, planted_date)` (not bed-adjacency) across all plantings; germination-check events skip `source_type == 'transplant'`. Germination-check and harvest events are actionable from the calendar. `harvests` is many-to-many with plantings (a planting can be picked repeatedly; yield/plant is computed, not stored) via `linked_planting_id`-style anchor rows, same pattern `garden_products`/`product_applications` reminders use (`linked_product_application_id`) for their own next-due `farm_events` regeneration.
- **`garden_products`/`product_applications`**: separate from `seed_varieties`' agronomic NPK guidance — this is the actual record of what product was applied where/when, so the gap between intended and actual feeding is itself a potential model feature.
- **Crop rotation / bed history** (commit `0d6a22b`): advisory (non-blocking) same-plant-family-within-N-years warning shown at planting-arm time, plus a "Rotation history" section on bed detail giving the multi-year per-bed planting view needed to judge it.
- **Frost-date planting validation**: `seed_varieties.frost_tolerance` (`tender`/`half_hardy`/`hardy`, ordinal like `sun_needs`) checked against farm-wide average frost dates (`farm_settings`, a singleton row edited on `/farm-settings`) via `farm/helpers.py`'s `frost_risk_windows`. Deliberately *not* shaped like the shade warning: shade is a permanent physical fact safe to snapshot once, but frost risk is only as good as its input data (today, an average date; eventually real weather), so the all-plantings page recomputes it live on every render instead of storing it — same pure function, called at render time instead of once at plant time. The bed-detail staging-time advisory (`/beds/{bed_id}/frost-warning`) *is* a one-time snapshot-style check, same reasoning as the rotation/shade advisories: it's a nudge at the moment of planting, not a live indicator. Tender/half-hardy plantings also get a `frost-cover` calendar event spanning the actual overlap between the grow window and the frost-risk window, flagged via `calendar_shared.day_square`'s new generic `critical` capability (see above) so it's visually impossible to miss.

**Next steps (proposed order, not yet started)**:
1. Weather/precipitation API ingestion — self-contained, no dependents, but unblocks frost-date accuracy (the live frost-risk indicator and the frost-cover event generation both take `last_frost_date`/`first_frost_date` as plain inputs, so swapping in real forecast data doesn't require touching either) and eventual dataset export.
2. Task list (harden off seedlings, thin rows, start indoors) generated from planting dates — germination/harvest event infra already exists, extend it to generic tasks.
3. Printable/exportable seasonal planting calendar.
4. Mobile-friendly bed entry — drag support exists, no responsive layout; bigger UI lift, not urgently wanted yet.
5. Cross-bed spacing/companion proximity — needs real map-space geometry between beds (not just one bed's grid); bigger lift, lower priority.
6. Photo attachment per bed — needs scoping against the existing variety reference-photo feature (seedling ID vs. bed documentation) before starting.

**Deferred** (too far out to schedule): exporting the accumulated planting/harvest/weather dataset (CSV/parquet) — blocked on accumulating enough real season data; the actual model training is out of scope for this app regardless.

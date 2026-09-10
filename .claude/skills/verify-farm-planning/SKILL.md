---
name: verify-farm-planning
description: Manually verify farm-planning features (land plots/beds, shade polygons/classification, seed varieties, plantings) against a live dev server. Use when a change to farm/ needs an end-to-end check beyond pytest -- e.g. confirming shade grows gradually across a season, a sun/shade warning actually fires, or a UI restructure renders as expected.
---

Drives the farm-planning subdomain's real HTTP routes with `requests` (installed in `.venv`)
instead of hand-writing `urllib` calls each time, plus a small Playwright screenshot helper for
visual checks. All paths below are relative to the repo root; run everything from there.

## Why this exists

`pytest tests/farm/` (including the Playwright-driven `test_land_map_js.py`/`test_bed_detail_js.py`)
already covers the JS/route mechanics in isolation against a throwaway `.env.test` database. This
skill is for the other kind of check: does the *feature* behave right when driven through the
real dev server and its real (gitignored) `.env` database -- e.g. "does the shade-grid tint
actually grow gradually across a season" or "does a sun/shade warning really fire for a variety
planted where shade will grow in", which are easier to eyeball live than to assert against a
JSON blob in a unit test.

**This mutates the real dev database.** Always create test rows with a distinctive name/label
prefix (`"Verify"` by default) and clean up with `farm_client.cleanup_by_prefix()` when done --
see Cleanup below.

## Setup

Same as `run-fasthtml-template-with-claude`:

```bash
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt   # requests + playwright already listed
playwright install chromium   # one-time, only needed for screenshot.py
```

`requests` is already in `.venv` (used by nothing else in the app itself, but available for
scripts like this).

## Run

Start the dev server, same as always:

```bash
source .venv/bin/activate
(python main.py > /tmp/fasthtml-server.log 2>&1 &)
timeout 30 bash -c 'until curl -sf http://localhost:5001 >/dev/null; do sleep 1; done'
```

Then drive it from a Python script (inline `python3 - <<'EOF' ... EOF`, or a throwaway file) that
imports both the client and `db` directly:

```python
import sys
sys.path.insert(0, ".claude/skills/verify-farm-planning")
from farm_client import FarmClient, cleanup_by_prefix
import db  # repo root -- reads the real dev database via .env

client = FarmClient()

client.add_land_plot("VerifyPlot", 20, 20)
plot_id = [p for p in db.list_land_plots() if p["name"] == "VerifyPlot"][0]["id"]

client.add_bed(plot_id, "VerifyBed", 6, 6)
bed_id = [b for b in db.list_beds_for_plot(plot_id) if b["label"] == "VerifyBed"][0]["id"]
client.place_bed(bed_id, 5, 5)

client.add_shade_source(plot_id, "VerifyTree")
source_id = db.list_shade_sources_for_plot(plot_id)[0]["id"]
client.save_shade_polygon(source_id, "summer_solstice", "full", [[0, 0], [0, 2], [2, 2], [2, 0]])
client.save_shade_polygon(source_id, "winter_solstice", "full", [[0, 0], [0, 20], [20, 20], [20, 0]])

# check gradual (not jumping) growth across the season
for on_date in ["2026-06-21", "2026-09-15", "2026-09-23", "2026-11-01", "2026-12-21"]:
    grid = client.shade_grid(bed_id, on_date)
    shaded = sum(1 for row in grid["cells"] for c in row if c != "full_sun")
    print(on_date, shaded, "/", grid["cols"] * grid["rows"])

cleanup_by_prefix()  # removes every "Verify"-prefixed plot/shade-source/variety
```

`FarmClient` methods (see `farm_client.py` for the full list and docstrings):

- `add_land_plot`, `add_bed`, `place_bed`, `delete_land_plot`
- `add_shade_source`, `save_shade_polygon`, `delete_shade_source`
- `shade_grid(bed_id, on_date=None)` -> `{"cols", "rows", "cells"}`, one classification per foot-cell
- `shade_warnings(bed_id, variety_id, planted_date, points_in)` -> `{"warnings": [bool, ...]}`
- `add_seed_variety(common_name, name, plant_family, **agronomic_fields)`, `delete_seed_variety`

Most routes redirect/render HTML rather than returning the new row's id, so look ids up via
`db.list_*`/`db.get_*` right after creating something, filtering on the name/label you just
used (see the example above) -- exactly how the app's own tests do it.

### Screenshots

```bash
python .claude/skills/verify-farm-planning/screenshot.py \
    "http://localhost:5001/land-plots/<plot_id>/map" /tmp/map.png \
    --click '.shade-type-toggle[data-shade-type="full"]'
```

`--click` is repeatable and applied in order before the shot -- use it to expand a collapsed
UI section (e.g. a shade type-group) before capturing. Then use the Read tool on the output PNG
to actually look at it.

## Cleanup

Always finish with:

```bash
python .claude/skills/verify-farm-planning/farm_client.py   # cleans up the default "Verify" prefix
```

or call `cleanup_by_prefix()` inline as in the example above. It deletes every land plot (and,
first, its shade sources -- `delete_land_plot` does NOT cascade those, only beds) and every seed
variety whose name/label starts with the prefix. Verify it actually ran (`removed = {...}` with
nonzero counts, or an empty-list check on `db.list_land_plots()` filtered to the prefix) --
an interrupted script leaves orphaned test rows in the real dev database.

Stop the server when done:

```bash
lsof -ti:5001 -sTCP:LISTEN | xargs -r kill
```

## Gotchas

- Same cwd requirement as `run-fasthtml-template-with-claude`: `db.py` resolves `.env`
  relative to the current working directory, so run everything from the repo root.
- `delete_land_plot` does not cascade shade sources (only beds) -- always delete a plot's shade
  sources before the plot itself, or use `cleanup_by_prefix`, which already gets this order right.
- `save_shade_polygon`'s points are clamped server-side to the plot's `width_ft`/`length_ft` --
  if you're testing clamping behavior itself, don't be surprised that out-of-bounds points you
  send come back clamped in `db.list_shade_polygons_for_source(...)["points"]`, that's the
  feature working, not a bug in the client.
- `shade_grid`/`shade_warnings` need the bed actually placed (`place_bed`) -- an unplaced bed
  (`x`/`y` NULL) always classifies as `full_sun` regardless of any shade polygon.

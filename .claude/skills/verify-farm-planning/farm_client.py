"""requests-based helper for manually driving the farm-planning subdomain's HTTP routes
against a live dev server (see SKILL.md). Import both this module and `db` (repo root) from
the repo root -- routes mostly redirect/render HTML rather than returning JSON with the new
row's id, so lookups go through `db` directly, the same way the app's own Playwright tests do.

Always create test rows through a distinctive name/label prefix (default "Verify") and clean
up with `cleanup_by_prefix` when done -- there is no separate test database for manual runs
like this; it's the real dev db (DB_PATH in .env).
"""
import json
import sys
from pathlib import Path

import requests

DEFAULT_PREFIX = "Verify"

_REPO_ROOT = Path(__file__).resolve().parents[3]


class FarmClient:
    def __init__(self, base_url="http://localhost:5001"):
        self.base_url = base_url
        self.session = requests.Session()

    def _post(self, path, data):
        response = self.session.post(self.base_url + path, data=data)
        response.raise_for_status()
        return response

    def _get(self, path):
        response = self.session.get(self.base_url + path)
        response.raise_for_status()
        return response

    # -- land plots / beds ---------------------------------------------------------------

    def add_land_plot(self, name, width_ft, length_ft):
        self._post("/land-plots", {"name": name, "width_ft": str(width_ft), "length_ft": str(length_ft)})

    def add_bed(self, plot_id, label, width_ft, length_ft):
        self._post(f"/land-plots/{plot_id}/beds", {"label": label, "width_ft": str(width_ft), "length_ft": str(length_ft)})

    def place_bed(self, bed_id, x, y):
        "Sets a bed's plot position directly (equivalent to a completed land-map.js drag)."
        self._post(f"/beds/{bed_id}/position", {"x": str(x), "y": str(y)})

    def delete_land_plot(self, plot_id):
        "Cascades the plot's beds (farm/db.py's delete_land_plot), but NOT its shade sources -- delete those first."
        self._post(f"/land-plots/{plot_id}/delete", {})

    # -- shade ----------------------------------------------------------------------------

    def add_shade_source(self, plot_id, label):
        self._post(f"/land-plots/{plot_id}/shade-sources", {"label": label})

    def save_shade_polygon(self, source_id, season, shade_type, points):
        "points: list of [x, y] plot-foot pairs. season: summer_solstice/winter_solstice. shade_type: full/partial."
        self._post(
            f"/shade-sources/{source_id}/polygons",
            {"season": season, "shade_type": shade_type, "points": json.dumps(points)},
        )

    def delete_shade_source(self, source_id):
        self._post(f"/shade-sources/{source_id}/delete", {})

    def shade_grid(self, bed_id, on_date=None):
        "Returns {'cols', 'rows', 'cells'} -- one classification per foot-cell, as of on_date (default today)."
        path = f"/beds/{bed_id}/shade-grid" + (f"?on_date={on_date}" if on_date else "")
        return self._get(path).json()

    def shade_warnings(self, bed_id, variety_id, planted_date, points_in):
        "points_in: list of {'x_in', 'y_in'} bed-local inch dicts. Returns {'warnings': [bool, ...]}."
        return self._post(
            f"/beds/{bed_id}/shade-warnings",
            {"variety_id": str(variety_id), "planted_date": planted_date, "points": json.dumps(points_in)},
        ).json()

    # -- seed varieties ---------------------------------------------------------------------

    def add_seed_variety(self, common_name, name, plant_family, **fields):
        "Extra agronomic fields (sun_needs, days_to_maturity_min/max, spacing_in, ...) are all optional strings."
        data = {"common_name": common_name, "name": name, "plant_family": plant_family}
        data.update({k: str(v) for k, v in fields.items()})
        self._post("/seed-varieties", data)

    def delete_seed_variety(self, variety_id):
        self._post(f"/seed-varieties/{variety_id}/delete", {})


def cleanup_by_prefix(prefix=DEFAULT_PREFIX):
    """Deletes every land plot, shade source, and seed variety whose name/label starts with
    `prefix`, leaving the real dev database exactly as it was before a manual verification run.
    Works regardless of cwd -- inserts the repo root onto sys.path itself so `import db` resolves
    (db.py resolves .env relative to cwd, but the repo root's .env is the real dev config
    either way as long as this file hasn't moved relative to the repo root)."""
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))
    import db

    removed = {"land_plots": 0, "shade_sources": 0, "seed_varieties": 0}
    for plot in db.list_land_plots():
        if not plot["name"].startswith(prefix):
            continue
        for source in db.list_shade_sources_for_plot(plot["id"]):
            db.delete_shade_source(source["id"])
            removed["shade_sources"] += 1
        db.delete_land_plot(plot["id"])
        removed["land_plots"] += 1
    for variety in db.list_seed_varieties():
        if variety["common_name"].startswith(prefix):
            db.delete_seed_variety(variety["id"])
            removed["seed_varieties"] += 1
    return removed


if __name__ == "__main__":
    import sys

    removed = cleanup_by_prefix(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PREFIX)
    print(f"cleaned up {removed}")

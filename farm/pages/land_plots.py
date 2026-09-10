import json

from fasthtml import common as fast
from fasthtml.svg import Svg, Rect, G, Text, Defs, Pattern, Path

from farm.layout import layout
from farm.helpers import parse_required_int, parse_optional_int, SEASON_OPTIONS, SHADE_TYPE_OPTIONS
import db

router = fast.APIRouter()

SEASON_LABELS = {"summer_solstice": "Summer solstice", "winter_solstice": "Winter solstice"}
SHADE_TYPE_LABELS = {"full": "Full shade", "partial": "Partial shade"}
SHADE_COMBOS = [(season, shade_type) for season in SEASON_OPTIONS for shade_type in SHADE_TYPE_OPTIONS]

# Bed labels are sized off the bed's own dimensions -- and the label text length, so a long
# label on a narrow bed shrinks to fit rather than overflowing -- so a label never dwarfs its
# bed. Kept in sync with the matching constants/logic in static/land-map.js (live resize).
LABEL_FONT_RATIO = 0.3
LABEL_FONT_MIN = 0.2
LABEL_FONT_MAX = 0.5
LABEL_CHAR_WIDTH_RATIO = 0.6  # rough average glyph width as a fraction of font-size
MIN_BED_DIM_FOR_LABEL = 1  # ft; below this no label fits legibly, so it's hidden


def _plot_form(action, submit_label, plot=None):
    return fast.Form(
        fast.Input(name="name", placeholder="Name", value=plot["name"] if plot else "", required=True),
        fast.Input(
            name="width_ft", type="number", placeholder="Width (ft)",
            value=plot["width_ft"] if plot else "", required=True,
        ),
        fast.Input(
            name="length_ft", type="number", placeholder="Length (ft)",
            value=plot["length_ft"] if plot else "", required=True,
        ),
        fast.Button(submit_label, type="submit"),
        method="post",
        action=action,
    )


def _plot_row(plot):
    return fast.Tr(
        fast.Td(fast.A(plot["name"], href=f"/land-plots/{plot['id']}/map")),
        fast.Td(f"{plot['width_ft']} x {plot['length_ft']} ft"),
        fast.Td(
            fast.A("Edit", href=f"/land-plots/{plot['id']}/edit"),
            fast.Form(
                fast.Button("Delete", type="submit"), method="post", action=f"/land-plots/{plot['id']}/delete"
            ),
        ),
    )


@router("/land-plots", methods=["get"])
def list_land_plots_page():
    plots = db.list_land_plots()
    rows = (
        [_plot_row(p) for p in plots]
        if plots
        else [fast.Tr(fast.Td("No land plots yet.", colspan="3"))]
    )
    table = fast.Table(
        fast.Thead(fast.Tr(fast.Th("Name"), fast.Th("Dimensions"), fast.Th(""))),
        fast.Tbody(*rows),
    )
    return layout(
        "Land Plots",
        fast.H1("Land Plots"),
        fast.H2("Add a land plot"),
        _plot_form(action="/land-plots", submit_label="Add Plot"),
        fast.H2("All plots"),
        table,
    )


def _validate_plot_fields(name, width_ft, length_ft):
    "Returns (name, width_ft, length_ft) or an error fast.Response."
    name = name.strip()
    if not name:
        return fast.Response("Name is required.", status_code=422)
    width_ft, error = parse_required_int(width_ft, "Width")
    if error:
        return fast.Response(error, status_code=422)
    length_ft, error = parse_required_int(length_ft, "Length")
    if error:
        return fast.Response(error, status_code=422)
    if width_ft <= 0:
        return fast.Response("Width must be a positive number.", status_code=422)
    if length_ft <= 0:
        return fast.Response("Length must be a positive number.", status_code=422)
    return name, width_ft, length_ft


@router("/land-plots", methods=["post"])
def add_land_plot_route(name: str, width_ft: str, length_ft: str):
    validated = _validate_plot_fields(name, width_ft, length_ft)
    if isinstance(validated, fast.Response):
        return validated
    name, width_ft, length_ft = validated
    db.add_land_plot(name, width_ft, length_ft)
    return fast.Redirect("/land-plots")


@router("/land-plots/{plot_id}/edit", methods=["get"])
def edit_land_plot_page(plot_id: int):
    plot = db.get_land_plot(plot_id)
    if plot is None:
        return fast.Response("Land plot not found.", status_code=404)
    return layout(
        "Edit Land Plot",
        fast.H1("Edit Land Plot"),
        _plot_form(action=f"/land-plots/{plot_id}/edit", submit_label="Save Changes", plot=plot),
    )


@router("/land-plots/{plot_id}/edit", methods=["post"])
def update_land_plot_route(plot_id: int, name: str, width_ft: str, length_ft: str):
    validated = _validate_plot_fields(name, width_ft, length_ft)
    if isinstance(validated, fast.Response):
        return validated
    name, width_ft, length_ft = validated
    db.update_land_plot(plot_id, name, width_ft, length_ft)
    return fast.Redirect("/land-plots")


@router("/land-plots/{plot_id}/delete", methods=["post"])
def delete_land_plot_route(plot_id: int):
    db.delete_land_plot(plot_id)
    return fast.Redirect("/land-plots")


def _add_bed_form(plot_id):
    return fast.Form(
        fast.Input(name="label", placeholder="Label (e.g. Bed 1)", required=True),
        fast.Input(name="width_ft", type="number", placeholder="Width (ft)", required=True),
        fast.Input(name="length_ft", type="number", placeholder="Length (ft)", required=True),
        fast.Button("Add Bed", type="submit"),
        method="post",
        action=f"/land-plots/{plot_id}/beds",
    )


def _unplaced_bed_item(bed):
    return fast.Li(
        fast.A(f"{bed['label']} ({bed['width_ft']} x {bed['length_ft']} ft)", href=f"/beds/{bed['id']}"),
        fast.Form(
            fast.Button("Add to map", type="submit"), method="post", action=f"/beds/{bed['id']}/place"
        ),
        cls="unplaced-bed-item",
    )


def _shade_combo_key(season, shade_type):
    return f"{season}:{shade_type}"


def _source_polygons_dict(source_id):
    """The source's up-to-4 polygons, keyed by every (season, shade_type) combo -- None where
    nothing's drawn yet, else {"id": polygon_id, "points": [[x,y],...]}."""
    rows = db.list_shade_polygons_for_source(source_id)
    by_key = {
        _shade_combo_key(r["season"], r["shade_type"]): {"id": r["id"], "points": json.loads(r["points"])}
        for r in rows
    }
    return {_shade_combo_key(season, shade_type): by_key.get(_shade_combo_key(season, shade_type)) for season, shade_type in SHADE_COMBOS}


def _shade_map_data(plot_id, shade_sources):
    return {
        "plot_id": plot_id,
        "shade_sources": [
            {"id": source["id"], "label": source["label"], "polygons": _source_polygons_dict(source["id"])}
            for source in shade_sources
        ],
    }


def _shade_combo_row(source, season, shade_type, polygon):
    drawn = polygon is not None
    return fast.Div(
        fast.Span(f"{SEASON_LABELS[season]} / {SHADE_TYPE_LABELS[shade_type]}"),
        fast.Button(
            "Edit" if drawn else "Draw",
            type="button",
            cls="shade-draw-button",
            data_source_id=str(source["id"]),
            data_season=season,
            data_shade_type=shade_type,
        ),
        fast.Button(
            "Delete",
            type="button",
            cls="shade-delete-polygon-button",
            data_polygon_id=str(polygon["id"]) if drawn else "",
            hidden=not drawn,
        ),
        cls="shade-combo-row",
        data_season=season,
        data_shade_type=shade_type,
    )


def _shade_type_group(source, shade_type, polygons_dict):
    "Two seasons required per type -- both need drawing before the type reads as complete."
    drawn_count = sum(
        polygons_dict[_shade_combo_key(season, shade_type)] is not None for season in SEASON_OPTIONS
    )
    badge = "Complete" if drawn_count == len(SEASON_OPTIONS) else f"{drawn_count}/{len(SEASON_OPTIONS)} — needs both seasons"
    return fast.Div(
        fast.Button(
            fast.Span(SHADE_TYPE_LABELS[shade_type]),
            fast.Span(badge, cls="shade-type-badge"),
            type="button",
            cls="shade-type-toggle",
            data_source_id=str(source["id"]),
            data_shade_type=shade_type,
        ),
        fast.Div(
            *[
                _shade_combo_row(source, season, shade_type, polygons_dict[_shade_combo_key(season, shade_type)])
                for season in SEASON_OPTIONS
            ],
            cls="shade-season-rows",
            hidden=True,
        ),
        cls="shade-type-group",
        data_shade_type=shade_type,
    )


def _shade_source_item(source, polygons_dict):
    return fast.Div(
        fast.Div(
            fast.Strong(source["label"]),
            fast.Form(
                fast.Button("Delete source", type="submit"),
                method="post",
                action=f"/shade-sources/{source['id']}/delete",
            ),
            cls="shade-source-header",
        ),
        *[_shade_type_group(source, shade_type, polygons_dict) for shade_type in SHADE_TYPE_OPTIONS],
        cls="shade-source-item",
        data_source_id=str(source["id"]),
    )


def _add_shade_source_form(plot_id):
    return fast.Form(
        fast.Input(name="label", placeholder="Shade source (e.g. Oak tree, Barn)", required=True),
        fast.Button("Add Source", type="submit"),
        method="post",
        action=f"/land-plots/{plot_id}/shade-sources",
    )


def _shade_sidebar(plot_id, shade_sources_data):
    sources = shade_sources_data["shade_sources"]
    return fast.Div(
        fast.H2("Shade sources"),
        fast.Div(*[_shade_source_item(source, source["polygons"]) for source in sources], id="shade-sources-list")
        if sources
        else fast.P("No shade sources yet.", id="shade-sources-list"),
        _add_shade_source_form(plot_id),
        cls="land-map-sidebar",
    )


def _label_font_size(width_ft, length_ft, label):
    "Returns None when no legible size fits the bed (caller hides the label in that case)."
    if min(width_ft, length_ft) < MIN_BED_DIM_FOR_LABEL:
        return None
    by_dim = min(width_ft, length_ft) * LABEL_FONT_RATIO
    by_width = (width_ft * 0.9) / (max(len(label), 1) * LABEL_CHAR_WIDTH_RATIO)
    font_size = min(LABEL_FONT_MAX, by_dim, by_width)
    return round(font_size, 2) if font_size >= LABEL_FONT_MIN else None


def _bed_group(bed):
    "Clicking (not dragging) a bed navigates to its detail page, where plantings and bed metadata are managed."
    x, y = bed["x"], bed["y"]
    center_x, center_y = bed["width_ft"] / 2, bed["length_ft"] / 2
    font_size = _label_font_size(bed["width_ft"], bed["length_ft"], bed["label"])
    return G(
        Rect(bed["width_ft"], bed["length_ft"], cls="bed-rect"),
        Text(
            bed["label"], x=center_x, y=center_y, text_anchor="middle", dominant_baseline="middle",
            cls="bed-label", font_size=font_size or LABEL_FONT_MIN,
            style="display:none" if font_size is None else None,
        ),
        Rect(1, 1, x=bed["width_ft"] - 1, y=bed["length_ft"] - 1, cls="resize-handle"),
        id=f"bed-{bed['id']}",
        cls="bed-group",
        transform=f"translate({x},{y}) rotate({bed['rotation_deg']},{center_x},{center_y})",
        # Guarded on window.__shadeDrawActive (set by land-map.js) so clicking a bed to place a
        # shade-polygon vertex over it doesn't navigate away instead.
        onclick=f"if (!window.__shadeDrawActive) window.location.href='/beds/{bed['id']}'",
    )


@router("/land-plots/{plot_id}/map", methods=["get"])
def land_plot_map_page(plot_id: int):
    plot = db.get_land_plot(plot_id)
    if plot is None:
        return fast.Response("Land plot not found.", status_code=404)
    beds = db.list_beds_for_plot(plot_id)
    placed_beds = [b for b in beds if b["x"] is not None and b["y"] is not None]
    unplaced_beds = [b for b in beds if b["x"] is None or b["y"] is None]
    shade_sources = db.list_shade_sources_for_plot(plot_id)
    shade_data = _shade_map_data(plot_id, shade_sources)
    canvas = Svg(
        Defs(
            Pattern(
                Path(d="M 1 0 L 0 0 0 1", cls="grid-line"),
                id="foot-grid", width=1, height=1, patternUnits="userSpaceOnUse",
            )
        ),
        Rect(plot["width_ft"], plot["length_ft"], cls="grid-bg"),
        Rect(plot["width_ft"], plot["length_ft"], cls="plot-boundary"),
        *[_bed_group(bed) for bed in placed_beds],
        G(id="shade-draw-layer"),
        viewBox=f"0 0 {plot['width_ft']} {plot['length_ft']}",
        cls="land-map-svg",
        id="land-map-svg",
        data_plot_width=str(plot["width_ft"]),
        data_plot_length=str(plot["length_ft"]),
    )
    compass = fast.Div(
        fast.Div("↑", cls="compass-arrow"),
        fast.Div("N", cls="compass-label"),
        cls="compass",
        title="Map is drawn with north at the top",
    )
    canvas_wrap = fast.Div(canvas, compass, cls="land-map-canvas-wrap")
    beds_sidebar = fast.Div(
        fast.H2("Unplaced beds"),
        fast.Ul(*[_unplaced_bed_item(b) for b in unplaced_beds]) if unplaced_beds else fast.P("None."),
        fast.H2("Add a bed"),
        _add_bed_form(plot_id),
        cls="land-map-sidebar",
    )
    return layout(
        f"{plot['name']} Map",
        fast.H1(f"{plot['name']} ({plot['width_ft']} x {plot['length_ft']} ft)"),
        fast.A("All plots", href="/land-plots"),
        fast.Script(json.dumps(shade_data), type="application/json", id="shade-map-data"),
        fast.Div(id="shade-draw-status", cls="shade-draw-status", hidden=True),
        fast.Div(canvas_wrap, beds_sidebar, _shade_sidebar(plot_id, shade_data), cls="land-map-layout"),
        fast.Script(src="/land-map.js"),
    )


def _validate_bed_dimensions(width_ft, length_ft):
    "Returns (width_ft, length_ft) or an error fast.Response."
    width_ft, error = parse_required_int(width_ft, "Width")
    if error:
        return fast.Response(error, status_code=422)
    length_ft, error = parse_required_int(length_ft, "Length")
    if error:
        return fast.Response(error, status_code=422)
    if width_ft <= 0:
        return fast.Response("Width must be a positive number.", status_code=422)
    if length_ft <= 0:
        return fast.Response("Length must be a positive number.", status_code=422)
    return width_ft, length_ft


@router("/land-plots/{plot_id}/beds", methods=["post"])
def add_bed_route(plot_id: int, label: str, width_ft: str, length_ft: str):
    label = label.strip()
    if not label:
        return fast.Response("Label is required.", status_code=422)
    validated = _validate_bed_dimensions(width_ft, length_ft)
    if isinstance(validated, fast.Response):
        return validated
    width_ft, length_ft = validated
    db.add_bed(plot_id, label, width_ft, length_ft)
    return fast.Redirect(f"/land-plots/{plot_id}/map")


def _clamp(value, low, high):
    return max(low, min(value, high))


@router("/beds/{bed_id}/position", methods=["post"])
def update_bed_position_route(bed_id: int, x: str, y: str):
    bed = db.get_bed(bed_id)
    if bed is None:
        return fast.Response("Bed not found.", status_code=404)
    x, error = parse_required_int(x, "X")
    if error:
        return fast.Response(error, status_code=422)
    y, error = parse_required_int(y, "Y")
    if error:
        return fast.Response(error, status_code=422)
    plot = db.get_land_plot(bed["plot_id"])
    x = _clamp(x, 0, max(0, plot["width_ft"] - bed["width_ft"]))
    y = _clamp(y, 0, max(0, plot["length_ft"] - bed["length_ft"]))
    db.update_bed_position(bed_id, x, y)
    return fast.Response(status_code=204)


def _next_placement_position(plot, placed_beds):
    "Diagonally offsets each newly-placed bed by 1ft so consecutive placements don't stack exactly."
    occupied = {(b["x"], b["y"]) for b in placed_beds}
    max_x = max(0, plot["width_ft"] - 1)
    max_y = max(0, plot["length_ft"] - 1)
    offset = 0
    while (min(offset, max_x), min(offset, max_y)) in occupied and offset < max(max_x, max_y):
        offset += 1
    return min(offset, max_x), min(offset, max_y)


@router("/beds/{bed_id}/place", methods=["post"])
def place_bed_route(bed_id: int):
    "Moves an unplaced bed onto the map -- the plain-form counterpart to /position (JS drag)."
    bed = db.get_bed(bed_id)
    if bed is None:
        return fast.Response("Bed not found.", status_code=404)
    plot = db.get_land_plot(bed["plot_id"])
    placed_beds = [b for b in db.list_beds_for_plot(bed["plot_id"]) if b["x"] is not None and b["y"] is not None]
    x, y = _next_placement_position(plot, placed_beds)
    db.update_bed_position(bed_id, x, y)
    return fast.Redirect(f"/land-plots/{bed['plot_id']}/map")


@router("/beds/{bed_id}/size", methods=["post"])
def update_bed_size_route(bed_id: int, width_ft: str, length_ft: str):
    bed = db.get_bed(bed_id)
    if bed is None:
        return fast.Response("Bed not found.", status_code=404)
    validated = _validate_bed_dimensions(width_ft, length_ft)
    if isinstance(validated, fast.Response):
        return validated
    width_ft, length_ft = validated
    plot = db.get_land_plot(bed["plot_id"])
    x, y = bed["x"] or 0, bed["y"] or 0
    width_ft = _clamp(width_ft, 1, max(1, plot["width_ft"] - x))
    length_ft = _clamp(length_ft, 1, max(1, plot["length_ft"] - y))
    db.update_bed_size(bed_id, width_ft, length_ft)
    return fast.Response(status_code=204)


def _bed_edit_form(bed):
    return fast.Form(
        fast.Input(name="label", placeholder="Label", value=bed["label"], required=True),
        fast.Input(name="width_ft", type="number", placeholder="Width (ft)", value=bed["width_ft"], required=True),
        fast.Input(name="length_ft", type="number", placeholder="Length (ft)", value=bed["length_ft"], required=True),
        fast.Input(
            name="rotation_deg", type="number", placeholder="Rotation (degrees)", value=bed["rotation_deg"],
            min="0", max="359",
        ),
        fast.Button("Save Changes", type="submit"),
        method="post",
        action=f"/beds/{bed['id']}/edit",
    )


@router("/beds/{bed_id}/edit-fragment", methods=["get"])
def bed_edit_fragment(bed_id: int):
    bed = db.get_bed(bed_id)
    if bed is None:
        return fast.Response("Bed not found.", status_code=404)
    return (
        fast.H3(bed["label"]),
        _bed_edit_form(bed),
        fast.Form(
            fast.Button("Delete", type="submit"), method="post", action=f"/beds/{bed_id}/delete"
        ),
        fast.Button("Close", type="button", onclick="document.getElementById('bed-dialog').close()"),
    )


@router("/beds/{bed_id}/edit", methods=["post"])
def update_bed_route(bed_id: int, label: str, width_ft: str, length_ft: str, rotation_deg: str = ""):
    bed = db.get_bed(bed_id)
    if bed is None:
        return fast.Response("Bed not found.", status_code=404)
    label = label.strip()
    if not label:
        return fast.Response("Label is required.", status_code=422)
    validated = _validate_bed_dimensions(width_ft, length_ft)
    if isinstance(validated, fast.Response):
        return validated
    width_ft, length_ft = validated
    ok, rotation_deg = parse_optional_int(rotation_deg)
    if not ok:
        return fast.Response("Rotation must be a number.", status_code=422)
    if rotation_deg is not None and not (0 <= rotation_deg <= 359):
        return fast.Response("Rotation must be between 0 and 359 degrees.", status_code=422)
    db.update_bed(bed_id, label, width_ft, length_ft, rotation_deg or 0)
    return fast.Redirect(f"/beds/{bed_id}")


@router("/beds/{bed_id}/delete", methods=["post"])
def delete_bed_route(bed_id: int):
    bed = db.get_bed(bed_id)
    if bed is None:
        return fast.Redirect("/land-plots")
    db.delete_bed(bed_id)
    return fast.Redirect(f"/land-plots/{bed['plot_id']}/map")


@router("/land-plots/{plot_id}/shade-sources", methods=["post"])
def add_shade_source_route(plot_id: int, label: str):
    plot = db.get_land_plot(plot_id)
    if plot is None:
        return fast.Response("Land plot not found.", status_code=404)
    label = label.strip()
    if not label:
        return fast.Response("Label is required.", status_code=422)
    db.add_shade_source(plot_id, label)
    return fast.Redirect(f"/land-plots/{plot_id}/map")


@router("/shade-sources/{source_id}/delete", methods=["post"])
def delete_shade_source_route(source_id: int):
    source = db.get_shade_source(source_id)
    if source is None:
        return fast.Redirect("/land-plots")
    db.delete_shade_source(source_id)
    return fast.Redirect(f"/land-plots/{source['plot_id']}/map")


def _validate_polygon_points(raw_points, width_ft, length_ft):
    """Returns (list of [x, y] float pairs, None) or (None, error_message). Points are clamped
    to the plot's bounds -- nothing outside the land is worth classifying, so a shade shape is
    capped at the plot edge rather than allowed to extend past it."""
    try:
        parsed = json.loads(raw_points)
    except (TypeError, ValueError):
        return None, "Invalid points payload."
    if not isinstance(parsed, list) or len(parsed) < 3:
        return None, "A shade polygon needs at least 3 points."
    points = []
    for item in parsed:
        try:
            x, y = float(item[0]), float(item[1])
        except (TypeError, ValueError, IndexError, KeyError):
            return None, "Invalid point payload."
        points.append([max(0.0, min(x, width_ft)), max(0.0, min(y, length_ft))])
    return points, None


@router("/shade-sources/{source_id}/polygons", methods=["post"])
def save_shade_polygon_route(source_id: int, season: str, shade_type: str, points: str):
    "Fetch-based -- land-map.js persists a drawn/edited polygon and syncs local state from the JSON response."
    source = db.get_shade_source(source_id)
    if source is None:
        return fast.Response("Shade source not found.", status_code=404)
    plot = db.get_land_plot(source["plot_id"])
    if season not in SEASON_OPTIONS:
        return fast.Response("Invalid season.", status_code=422)
    if shade_type not in SHADE_TYPE_OPTIONS:
        return fast.Response("Invalid shade type.", status_code=422)
    parsed_points, error = _validate_polygon_points(points, plot["width_ft"], plot["length_ft"])
    if error:
        return fast.Response(error, status_code=422)
    polygon_id = db.save_shade_polygon(source_id, season, shade_type, json.dumps(parsed_points))
    return fast.Response(json.dumps({"id": polygon_id, "points": parsed_points}), media_type="application/json")


@router("/shade-polygons/{polygon_id}/delete", methods=["post"])
def delete_shade_polygon_route(polygon_id: int):
    if db.get_shade_polygon(polygon_id) is None:
        return fast.Response("Shade polygon not found.", status_code=404)
    db.delete_shade_polygon(polygon_id)
    return fast.Response(status_code=204)


# Bed detail rendering (variety-palette + spacing-lattice planting UI) lives in
# farm/pages/plantings.py -- it's planting-centric, same reasoning that already put the old
# cell routes there instead of here.

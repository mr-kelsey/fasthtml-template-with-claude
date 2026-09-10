import json
from datetime import date

from fasthtml import common as fast
from fasthtml.svg import Svg, Rect, Circle, G, Defs, Pattern, Path

from farm import geometry
from farm.layout import layout
from farm.helpers import parse_optional_int, parse_optional_float, parse_required_float, compute_window
import db

router = fast.APIRouter()


def _optional_value(planting, field):
    if planting is None or planting[field] is None:
        return ""
    return planting[field]


def _parse_date_or_none(value: str):
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _format_window(window):
    if window is None:
        return "-"
    start, end = window
    return start.isoformat() if start == end else f"{start.isoformat()} to {end.isoformat()}"


def _overlap_warnings(plantings):
    "Plantings sharing a non-blank location whose expected harvest windows intersect warn each other."
    warnings = {}
    by_location = {}
    for planting in plantings:
        location = (planting["location"] or "").strip()
        if location:
            by_location.setdefault(location, []).append(planting)
    for location, group in by_location.items():
        for i, first in enumerate(group):
            first_window = compute_window(first["planted_date"], first["days_to_maturity_min"], first["days_to_maturity_max"])
            if first_window is None:
                continue
            for second in group[i + 1 :]:
                second_window = compute_window(
                    second["planted_date"], second["days_to_maturity_min"], second["days_to_maturity_max"]
                )
                if second_window is None:
                    continue
                if max(first_window[0], second_window[0]) <= min(first_window[1], second_window[1]):
                    warnings.setdefault(first["id"], []).append(
                        f"Overlaps with {second['variety_name']} (planted {second['planted_date']}) at {location}"
                    )
                    warnings.setdefault(second["id"], []).append(
                        f"Overlaps with {first['variety_name']} (planted {first['planted_date']}) at {location}"
                    )
    return warnings


def _planting_form(action, submit_label, varieties, planting=None):
    selected_variety_id = planting["variety_id"] if planting else None
    return fast.Form(
        fast.Select(
            *[
                fast.Option(
                    f"{variety['common_name']} - {variety['name']}",
                    value=str(variety["id"]),
                    selected=(variety["id"] == selected_variety_id),
                )
                for variety in varieties
            ],
            name="variety_id",
            required=True,
        ),
        fast.Input(
            name="planted_date", type="date", value=planting["planted_date"] if planting else "", required=True
        ),
        fast.Input(
            name="location",
            placeholder="Location (optional, e.g. Bed 3 row 2)",
            value=(planting["location"] or "") if planting else "",
        ),
        fast.Input(name="quantity", type="number", placeholder="Quantity", value=_optional_value(planting, "quantity")),
        fast.Input(
            name="quantity_germinated",
            type="number",
            placeholder="Quantity germinated",
            value=_optional_value(planting, "quantity_germinated"),
        ),
        fast.Input(
            name="quantity_culled",
            type="number",
            placeholder="Quantity culled",
            value=_optional_value(planting, "quantity_culled"),
        ),
        fast.Textarea(
            planting["notes"] or "" if planting else "", name="notes", placeholder="Notes (optional)"
        ),
        fast.Button(submit_label, type="submit"),
        method="post",
        action=action,
    )


def _planting_row(planting, warnings):
    row_warnings = warnings.get(planting["id"], [])
    germination_window = compute_window(planting["planted_date"], planting["germination_days_min"], planting["germination_days_max"])
    harvest_window = compute_window(planting["planted_date"], planting["days_to_maturity_min"], planting["days_to_maturity_max"])
    return fast.Tr(
        fast.Td(planting["variety_name"] or ""),
        fast.Td(planting["common_name"] or ""),
        fast.Td(planting["planted_date"]),
        fast.Td(planting["location"] or ""),
        fast.Td(planting["quantity"] if planting["quantity"] is not None else ""),
        fast.Td(planting["quantity_germinated"] if planting["quantity_germinated"] is not None else ""),
        fast.Td(_format_window(germination_window)),
        fast.Td(_format_window(harvest_window)),
        fast.Td(
            fast.Ul(*[fast.Li(w, cls="overlap-warning") for w in row_warnings]) if row_warnings else ""
        ),
        fast.Td(
            fast.A("Edit", href=f"/plantings/{planting['id']}/edit"),
            fast.Form(
                fast.Button("Delete", type="submit"), method="post", action=f"/plantings/{planting['id']}/delete"
            ),
        ),
    )


@router("/plantings", methods=["get"])
def list_plantings_page():
    varieties = db.list_seed_varieties()
    plantings = db.list_plantings()
    warnings = _overlap_warnings(plantings)
    headers = [
        "Variety", "Common Name", "Planted", "Location", "Qty", "Germinated",
        "Germination window", "Harvest window", "Warnings", "",
    ]
    rows = (
        [_planting_row(p, warnings) for p in plantings]
        if plantings
        else [fast.Tr(fast.Td("No plantings yet.", colspan=str(len(headers))))]
    )
    table = fast.Table(
        fast.Thead(fast.Tr(*[fast.Th(h) for h in headers])),
        fast.Tbody(*rows),
    )
    add_section = (
        (
            fast.H2("Add a planting"),
            _planting_form(action="/plantings", submit_label="Add Planting", varieties=varieties),
        )
        if varieties
        else (fast.P(fast.A("Add a seed variety", href="/seed-varieties"), " first before recording plantings."),)
    )
    return layout(
        "Plantings",
        fast.H1("Plantings"),
        *add_section,
        fast.H2("All plantings"),
        table,
    )


def _validate_variety_id(variety_id: str):
    "Returns the int variety_id if it references an existing seed variety, or an error fast.Response."
    ok, parsed_variety_id = (True, int(variety_id)) if variety_id.strip().isdigit() else (False, None)
    if not ok or db.get_seed_variety(parsed_variety_id) is None:
        return fast.Response("Choose a valid seed variety.", status_code=422)
    return parsed_variety_id


def _validate_planting_fields(variety_id, planted_date, quantity, quantity_germinated, quantity_culled):
    "Returns (variety_id, planted_date, quantity, quantity_germinated, quantity_culled) or an error fast.Response."
    validated_variety_id = _validate_variety_id(variety_id)
    if isinstance(validated_variety_id, fast.Response):
        return validated_variety_id
    planted_date = planted_date.strip()
    if not planted_date or _parse_date_or_none(planted_date) is None:
        return fast.Response("Invalid planted date.", status_code=422)
    ok, quantity = parse_optional_int(quantity)
    if not ok:
        return fast.Response("Quantity must be a number.", status_code=422)
    ok, quantity_germinated = parse_optional_int(quantity_germinated)
    if not ok:
        return fast.Response("Quantity germinated must be a number.", status_code=422)
    ok, quantity_culled = parse_optional_int(quantity_culled)
    if not ok:
        return fast.Response("Quantity culled must be a number.", status_code=422)
    if quantity_culled is not None and (quantity_germinated is None or quantity_culled > quantity_germinated):
        return fast.Response("Quantity culled cannot exceed quantity germinated.", status_code=422)
    return validated_variety_id, planted_date, quantity, quantity_germinated, quantity_culled


@router("/plantings", methods=["post"])
def add_planting_route(
    variety_id: str,
    planted_date: str,
    location: str = "",
    quantity: str = "",
    quantity_germinated: str = "",
    quantity_culled: str = "",
    notes: str = "",
):
    validated = _validate_planting_fields(variety_id, planted_date, quantity, quantity_germinated, quantity_culled)
    if isinstance(validated, fast.Response):
        return validated
    variety_id, planted_date, quantity, quantity_germinated, quantity_culled = validated
    db.add_planting(
        variety_id,
        planted_date,
        location=location.strip() or None,
        quantity=quantity,
        quantity_germinated=quantity_germinated,
        quantity_culled=quantity_culled,
        notes=notes.strip() or None,
    )
    return fast.Redirect("/plantings")


def _yield_summary(planting, harvests):
    "Living plants, total harvested, and computed (not stored) yield-per-plant, alongside the harvest log."
    living = None
    if planting["quantity_germinated"] is not None:
        living = planting["quantity_germinated"] - (planting["quantity_culled"] or 0)
    total_weight = sum(h["weight_lb"] for h in harvests)
    yield_per_plant = total_weight / living if living else None
    harvest_rows = [
        fast.Li(
            f"{h['harvest_date']}: {h['weight_lb']} lb" + (f" — {h['notes']}" if h["notes"] else ""),
            " ",
            fast.A("Edit", href=f"/harvests/{h['id']}/edit"),
            fast.Form(
                fast.Button("Delete", type="submit"), method="post", action=f"/harvests/{h['id']}/delete"
            ),
        )
        for h in harvests
    ]
    return fast.Div(
        fast.H2("Yield"),
        fast.P(f"Living plants: {living if living is not None else 'unknown'}"),
        fast.P(f"Total harvested: {total_weight} lb") if harvests else fast.P("No harvests logged yet."),
        fast.P(f"Yield per plant: {yield_per_plant:.2f} lb/plant") if yield_per_plant is not None else "",
        fast.H3("Harvest history") if harvests else "",
        fast.Ul(*harvest_rows) if harvests else "",
        fast.H3("Log a harvest"),
        fast.Form(
            fast.Input(name="harvest_date", type="date", required=True),
            fast.Input(name="weight_lb", type="number", step="0.01", placeholder="Weight (lb)", required=True),
            fast.Textarea("", name="notes", placeholder="Notes (optional)"),
            fast.Button("Log Harvest", type="submit"),
            method="post",
            action=f"/plantings/{planting['id']}/harvests",
        ),
    )


@router("/plantings/{planting_id}/edit", methods=["get"])
def edit_planting_page(planting_id: int):
    planting = db.get_planting(planting_id)
    if planting is None:
        return fast.Response("Planting not found.", status_code=404)
    return layout(
        "Edit Planting",
        fast.H1("Edit Planting"),
        _planting_form(
            action=f"/plantings/{planting_id}/edit",
            submit_label="Save Changes",
            varieties=db.list_seed_varieties(),
            planting=planting,
        ),
        _yield_summary(planting, db.list_harvests_for_planting(planting_id)),
    )


@router("/plantings/{planting_id}/edit", methods=["post"])
def update_planting_route(
    planting_id: int,
    variety_id: str,
    planted_date: str,
    location: str = "",
    quantity: str = "",
    quantity_germinated: str = "",
    quantity_culled: str = "",
    notes: str = "",
):
    existing = db.get_planting(planting_id)
    if existing is None:
        return fast.Response("Planting not found.", status_code=404)
    validated = _validate_planting_fields(variety_id, planted_date, quantity, quantity_germinated, quantity_culled)
    if isinstance(validated, fast.Response):
        return validated
    variety_id, planted_date, quantity, quantity_germinated, quantity_culled = validated
    db.update_planting(
        planting_id,
        variety_id,
        planted_date,
        bed_id=existing["bed_id"],
        location=location.strip() or None,
        quantity=quantity,
        quantity_germinated=quantity_germinated,
        quantity_culled=quantity_culled,
        notes=notes.strip() or None,
        x_in=existing["x_in"],
        y_in=existing["y_in"],
        seed_lot_id=existing["seed_lot_id"],
        transplant_lot_id=existing["transplant_lot_id"],
        source_type=existing["source_type"],
        soil_temp_f=existing["soil_temp_f"],
    )
    if existing["bed_id"] is not None:
        return fast.Redirect(f"/beds/{existing['bed_id']}")
    return fast.Redirect("/plantings")


def _validate_harvest_fields(harvest_date, weight_lb):
    "Returns (harvest_date, weight_lb) or an error fast.Response."
    harvest_date = harvest_date.strip()
    if not harvest_date or _parse_date_or_none(harvest_date) is None:
        return fast.Response("Invalid harvest date.", status_code=422)
    weight_lb, error = parse_required_float(weight_lb, "Weight")
    if error:
        return fast.Response(error, status_code=422)
    return harvest_date, weight_lb


@router("/plantings/{planting_id}/harvests", methods=["post"])
def add_harvest_route(planting_id: int, harvest_date: str, weight_lb: str, notes: str = ""):
    planting = db.get_planting(planting_id)
    if planting is None:
        return fast.Response("Planting not found.", status_code=404)
    validated = _validate_harvest_fields(harvest_date, weight_lb)
    if isinstance(validated, fast.Response):
        return validated
    harvest_date, weight_lb = validated
    db.add_harvest(planting_id, harvest_date, weight_lb, notes=notes.strip() or None)
    return fast.Redirect(f"/plantings/{planting_id}/edit")


def _harvest_form(action, harvest):
    return fast.Form(
        fast.Input(name="harvest_date", type="date", value=harvest["harvest_date"], required=True),
        fast.Input(name="weight_lb", type="number", step="0.01", value=harvest["weight_lb"], required=True),
        fast.Textarea(harvest["notes"] or "", name="notes", placeholder="Notes (optional)"),
        fast.Button("Save Changes", type="submit"),
        method="post",
        action=action,
    )


@router("/harvests/{harvest_id}/edit", methods=["get"])
def edit_harvest_page(harvest_id: int):
    harvest = db.get_harvest(harvest_id)
    if harvest is None:
        return fast.Response("Harvest not found.", status_code=404)
    return layout(
        "Edit Harvest",
        fast.H1("Edit Harvest"),
        _harvest_form(action=f"/harvests/{harvest_id}/edit", harvest=harvest),
    )


@router("/harvests/{harvest_id}/edit", methods=["post"])
def update_harvest_route(harvest_id: int, harvest_date: str, weight_lb: str, notes: str = ""):
    harvest = db.get_harvest(harvest_id)
    if harvest is None:
        return fast.Response("Harvest not found.", status_code=404)
    validated = _validate_harvest_fields(harvest_date, weight_lb)
    if isinstance(validated, fast.Response):
        return validated
    harvest_date, weight_lb = validated
    db.update_harvest(harvest_id, harvest_date, weight_lb, notes=notes.strip() or None)
    return fast.Redirect(f"/plantings/{harvest['planting_id']}/edit")


@router("/harvests/{harvest_id}/delete", methods=["post"])
def delete_harvest_route(harvest_id: int):
    harvest = db.get_harvest(harvest_id)
    if harvest is None:
        return fast.Redirect("/plantings")
    db.delete_harvest(harvest_id)
    return fast.Redirect(f"/plantings/{harvest['planting_id']}/edit")


@router("/plantings/{planting_id}/delete", methods=["post"])
def delete_planting_route(planting_id: int):
    planting = db.get_planting(planting_id)
    if planting is None:
        return fast.Redirect("/plantings")
    db.delete_planting(planting_id)
    if planting["bed_id"] is not None:
        return fast.Redirect(f"/beds/{planting['bed_id']}")
    return fast.Redirect("/plantings")


@router("/plantings/{planting_id}/lineage", methods=["get"])
def planting_lineage_page(planting_id: int):
    "Walks transplant_lot_id -> transplant_lots.origin_planting_id to find the self-grown nursery planting, if any."
    planting = db.get_planting(planting_id)
    if planting is None:
        return fast.Response("Planting not found.", status_code=404)
    variety = db.get_seed_variety(planting["variety_id"])
    variety_label = f"{variety['common_name']} - {variety['name']}" if variety else "Unknown variety"
    lineage_content = (fast.P("This planting was grown from seed -- no transplant lineage to show."),)
    if planting["source_type"] == "transplant" and planting["transplant_lot_id"] is not None:
        lot = db.get_transplant_lot(planting["transplant_lot_id"])
        if lot is None:
            lineage_content = (fast.P("The transplant lot for this planting no longer exists."),)
        elif lot["origin_planting_id"] is not None:
            origin = db.get_planting(lot["origin_planting_id"])
            if origin is None:
                lineage_content = (fast.P("The origin planting for this lot no longer exists."),)
            else:
                origin_variety = db.get_seed_variety(origin["variety_id"])
                origin_label = (
                    f"{origin_variety['common_name']} - {origin_variety['name']}" if origin_variety else "Unknown variety"
                )
                lineage_content = (
                    fast.P("Self-grown from:"),
                    fast.P(
                        fast.A(
                            f"{origin_label} planted {origin['planted_date']} (#{origin['id']})",
                            href=f"/plantings/{origin['id']}/edit",
                        )
                    ),
                )
        else:
            lineage_content = (
                fast.P("Purchased:"),
                fast.Ul(
                    fast.Li(f"Source: {lot['purchased_source'] or 'unknown'}"),
                    fast.Li(f"Vendor: {lot['purchased_vendor'] or 'unknown'}"),
                    fast.Li(f"Date: {lot['purchased_date'] or 'unknown'}"),
                ),
            )
    return layout(
        "Planting Lineage",
        fast.H1(f"Lineage: {variety_label} (#{planting_id})"),
        *lineage_content,
    )


def _planting_dot(planting):
    "An already-persisted planting, rendered at its real inch position in the variety's color."
    return Circle(
        2, cx=planting["x_in"], cy=planting["y_in"], fill=planting["color_hex"] or "#888888",
        cls="planting-dot", data_planting_id=str(planting["id"]), data_variety_id=str(planting["variety_id"]),
        data_common_name=planting["common_name"] or "",
    )


DOT_RADIUS_IN = 2  # planting-dot / lattice-point circle radius, in the same inch units as the viewBox
CANVAS_MARGIN_IN = DOT_RADIUS_IN + 1  # viewBox padding so edge/corner points (x_in or y_in == 0 or the bed's max)
# aren't clipped by the SVG's own boundary -- their circles would otherwise be cut in half, both visually and
# for hit-testing (a corner lattice point at (0, length_in) is a real, common click target: bed edges/border
# rows), since the root <svg> clips content outside its viewBox.


def _bed_canvas(bed, plantings):
    width_in = bed["width_ft"] * 12
    length_in = bed["length_ft"] * 12
    return Svg(
        Defs(
            Pattern(
                Path(d="M 12 0 L 0 0 0 12", cls="grid-line-detail"),
                id="inch-foot-grid", width=12, height=12, patternUnits="userSpaceOnUse",
            )
        ),
        Rect(width_in, length_in, cls="grid-bg-detail"),
        Rect(width_in, length_in, cls="bed-boundary"),
        G(id="shade-layer"),
        G(*[_planting_dot(p) for p in plantings if p["x_in"] is not None], id="planted-layer"),
        G(id="lattice-layer"),
        G(id="staged-layer"),
        viewBox=f"{-CANVAS_MARGIN_IN} {-CANVAS_MARGIN_IN} {width_in + 2 * CANVAS_MARGIN_IN} {length_in + 2 * CANVAS_MARGIN_IN}",
        cls="bed-detail-svg",
        id="bed-detail-svg",
        data_width_in=str(width_in),
        data_length_in=str(length_in),
    )


def _palette_item(variety, mode):
    return fast.Button(
        fast.Span(cls="variety-swatch", style=f"background-color:{variety['color_hex'] or '#888888'}"),
        f" {variety['common_name']} - {variety['name']}",
        type="button",
        cls="variety-palette-item",
        data_variety_id=str(variety["id"]),
        data_mode=mode,
    )


def _bed_detail_data(bed, plantings, seed_stock_varieties, transplant_stock_varieties, transplant_lots_by_variety, companion_rules):
    return {
        "bed_id": bed["id"],
        "width_in": bed["width_ft"] * 12,
        "length_in": bed["length_ft"] * 12,
        "plantings": [
            {
                "id": p["id"], "variety_id": p["variety_id"], "common_name": p["common_name"],
                "x_in": p["x_in"], "y_in": p["y_in"], "color_hex": p["color_hex"] or "#888888",
            }
            for p in plantings
            if p["x_in"] is not None
        ],
        "seed_varieties": [
            {
                "id": v["id"], "common_name": v["common_name"], "name": v["name"],
                "spacing_in": v["spacing_in"], "color_hex": v["color_hex"] or "#888888",
            }
            for v in seed_stock_varieties
        ],
        "transplant_varieties": [
            {
                "id": v["id"], "common_name": v["common_name"], "name": v["name"],
                "spacing_in": v["spacing_in"], "color_hex": v["color_hex"] or "#888888",
            }
            for v in transplant_stock_varieties
        ],
        "transplant_lots_by_variety": {
            str(variety_id): [{"id": lot["id"], "quantity_on_hand": lot["quantity_on_hand"]} for lot in lots]
            for variety_id, lots in transplant_lots_by_variety.items()
        },
        "companion_rules": [
            {"a": r["plant_a_common_name"], "b": r["plant_b_common_name"], "relation": r["relation"]}
            for r in companion_rules
        ],
    }


def _batch_plant_form(bed_id):
    return fast.Form(
        fast.Input(type="hidden", name="variety_id", id="batch-variety-id"),
        fast.Input(type="hidden", name="source_type", id="batch-source-type"),
        fast.Input(type="hidden", name="points", id="batch-points"),
        fast.Div(id="batch-staged-count"),
        fast.Input(name="planted_date", type="date", id="batch-planted-date", required=True),
        fast.Input(name="soil_temp_f", type="number", step="0.1", placeholder="Soil temp (F, optional)"),
        fast.Select(fast.Option("Choose a transplant lot", value=""), name="transplant_lot_id", id="batch-transplant-lot-select", hidden=True),
        fast.Label(
            "On hand in this lot:",
            fast.Input(type="number", min="0", id="armed-lot-quantity-input"),
            id="armed-lot-quantity-wrap",
            hidden=True,
        ),
        fast.Button("Plant staged points", type="submit"),
        method="post",
        action=f"/beds/{bed_id}/cells/batch",
        id="batch-plant-form",
        hidden=True,
    )


@router("/beds/{bed_id}", methods=["get"])
def bed_detail_page(bed_id: int):
    bed = db.get_bed(bed_id)
    if bed is None:
        return fast.Response("Bed not found.", status_code=404)
    plantings = db.list_plantings_for_bed(bed_id)
    seed_stock_varieties = db.list_seed_varieties_with_seed_stock()
    transplant_stock_varieties = db.list_seed_varieties_with_transplant_stock()
    transplant_lots_by_variety = {
        v["id"]: db.list_available_transplant_lots_for_variety(v["id"]) for v in transplant_stock_varieties
    }
    companion_rules = db.list_companion_rules()
    data = _bed_detail_data(
        bed, plantings, seed_stock_varieties, transplant_stock_varieties, transplant_lots_by_variety, companion_rules
    )
    canvas = _bed_canvas(bed, plantings)
    palette = fast.Div(
        fast.Fieldset(
            fast.Label(
                fast.Input(type="radio", name="mode", value="seed", checked=True, id="mode-seed"), " Direct sow"
            ),
            fast.Label(
                fast.Input(type="radio", name="mode", value="transplant", id="mode-transplant"), " Transplant"
            ),
        ),
        fast.Div(
            *(
                [_palette_item(v, "seed") for v in seed_stock_varieties]
                if seed_stock_varieties
                else [fast.P("No varieties with seed stock on hand.")]
            ),
            id="palette-seed",
            cls="variety-palette",
        ),
        fast.Div(
            *(
                [_palette_item(v, "transplant") for v in transplant_stock_varieties]
                if transplant_stock_varieties
                else [fast.P("No varieties with transplant stock on hand.")]
            ),
            id="palette-transplant",
            cls="variety-palette",
            hidden=True,
        ),
        cls="bed-detail-sidebar",
    )
    edit_bed_button = fast.Button(
        "Edit bed",
        type="button",
        hx_get=f"/beds/{bed_id}/edit-fragment",
        hx_target="#bed-dialog-body",
        hx_trigger="click",
        hx_on__after_request="document.getElementById('bed-dialog').showModal()",
    )
    shade_date_picker = fast.Label(
        "Shade as of:", fast.Input(type="date", id="shade-date", value=date.today().isoformat())
    )
    return layout(
        f"{bed['label']} Detail",
        fast.H1(f"{bed['label']} ({bed['width_ft']} x {bed['length_ft']} ft)"),
        fast.A("Back to plot map", href=f"/land-plots/{bed['plot_id']}/map"),
        edit_bed_button,
        shade_date_picker,
        fast.Script(json.dumps(data), type="application/json", id="bed-detail-data"),
        fast.Div(canvas, palette, cls="bed-detail-layout"),
        _batch_plant_form(bed_id),
        fast.Dialog(fast.Div(id="bed-dialog-body"), id="bed-dialog"),
        fast.Script(src="/bed-detail.js"),
    )


def _validate_points(raw_points, width_in, length_in):
    "Returns (list of (x_in, y_in) tuples, None) or (None, error_message)."
    try:
        parsed = json.loads(raw_points)
    except (TypeError, ValueError):
        return None, "Invalid points payload."
    if not isinstance(parsed, list) or not parsed:
        return None, "At least one staged point is required."
    points = []
    for item in parsed:
        try:
            x_in, y_in = float(item["x_in"]), float(item["y_in"])
        except (KeyError, TypeError, ValueError):
            return None, "Invalid point payload."
        if not (0 <= x_in <= width_in) or not (0 <= y_in <= length_in):
            return None, "A staged point falls outside the bed."
        points.append((x_in, y_in))
    return points, None


@router("/beds/{bed_id}/cells/batch", methods=["post"])
def batch_plant_route(
    bed_id: int,
    variety_id: str,
    source_type: str,
    planted_date: str,
    points: str,
    soil_temp_f: str = "",
    transplant_lot_id: str = "",
):
    "Stamps a batch of staged lattice points for one variety into the bed in one submission."
    bed = db.get_bed(bed_id)
    if bed is None:
        return fast.Response("Bed not found.", status_code=404)
    validated_variety_id = _validate_variety_id(variety_id)
    if isinstance(validated_variety_id, fast.Response):
        return validated_variety_id
    variety_id = validated_variety_id
    planted_date = planted_date.strip()
    if not planted_date or _parse_date_or_none(planted_date) is None:
        return fast.Response("Invalid planted date.", status_code=422)
    if source_type not in ("seed", "transplant"):
        return fast.Response("Invalid source type.", status_code=422)
    width_in = bed["width_ft"] * 12
    length_in = bed["length_ft"] * 12
    parsed_points, error = _validate_points(points, width_in, length_in)
    if error:
        return fast.Response(error, status_code=422)
    ok, soil_temp_f_value = parse_optional_float(soil_temp_f)
    if not ok:
        return fast.Response("Soil temp must be a number.", status_code=422)
    validated_transplant_lot_id = None
    if source_type == "seed":
        if not db.list_seed_lots_for_variety(variety_id):
            return fast.Response("This variety has no seed lots on hand.", status_code=422)
    else:
        ok, lot_id = parse_optional_int(transplant_lot_id)
        if not ok or lot_id is None:
            return fast.Response("Choose a transplant lot.", status_code=422)
        lot = db.get_transplant_lot(lot_id)
        if lot is None or lot["variety_id"] != variety_id:
            return fast.Response("Invalid transplant lot for this variety.", status_code=422)
        if lot["quantity_on_hand"] is None or len(parsed_points) > lot["quantity_on_hand"]:
            return fast.Response("Not enough transplants on hand in that lot.", status_code=422)
        validated_transplant_lot_id = lot_id
    db.batch_add_plantings(
        variety_id, planted_date, bed_id, source_type, parsed_points,
        transplant_lot_id=validated_transplant_lot_id, soil_temp_f=soil_temp_f_value,
    )
    return fast.Redirect(f"/beds/{bed_id}")


def _load_shade_polygons(plot_id):
    "shade_polygons_for_plot's rows with points parsed into (x, y) tuples, ready for farm.geometry."
    rows = db.list_shade_polygons_for_plot(plot_id)
    return [
        {"season": r["season"], "shade_type": r["shade_type"], "points": [tuple(p) for p in json.loads(r["points"])]}
        for r in rows
    ]


@router("/beds/{bed_id}/shade-grid", methods=["get"])
def bed_shade_grid_route(bed_id: int, on_date: str = ""):
    "One classified cell per foot -- the existing 12in grid is already exactly width_ft x length_ft cells."
    bed = db.get_bed(bed_id)
    if bed is None:
        return fast.Response("Bed not found.", status_code=404)
    day = _parse_date_or_none(on_date) or date.today()
    shade_polygons = _load_shade_polygons(bed["plot_id"])
    cols, rows = bed["width_ft"], bed["length_ft"]
    cells = [
        [geometry.classify_bed_cell_shade(bed, col * 12 + 6, row * 12 + 6, day, shade_polygons) for col in range(cols)]
        for row in range(rows)
    ]
    return fast.Response(json.dumps({"cols": cols, "rows": rows, "cells": cells}), media_type="application/json")


@router("/beds/{bed_id}/shade-warnings", methods=["post"])
def bed_shade_warnings_route(bed_id: int, variety_id: str, planted_date: str, points: str):
    "Returns {'warnings': [bool, ...]} in the same order as the submitted points -- non-blocking, decoration only."
    bed = db.get_bed(bed_id)
    if bed is None:
        return fast.Response("Bed not found.", status_code=404)
    validated_variety_id = _validate_variety_id(variety_id)
    if isinstance(validated_variety_id, fast.Response):
        return validated_variety_id
    variety = db.get_seed_variety(validated_variety_id)
    planted = _parse_date_or_none(planted_date)
    if planted is None:
        return fast.Response("Invalid planted date.", status_code=422)
    width_in = bed["width_ft"] * 12
    length_in = bed["length_ft"] * 12
    parsed_points, error = _validate_points(points, width_in, length_in)
    if error:
        return fast.Response(error, status_code=422)
    window = compute_window(planted_date, variety["days_to_maturity_min"], variety["days_to_maturity_max"])
    maturity_end = window[1] if window else planted
    shade_polygons = _load_shade_polygons(bed["plot_id"])
    warnings = [
        geometry.shade_exceeds_tolerance(bed, x_in, y_in, planted, maturity_end, variety["sun_needs"], shade_polygons)
        for x_in, y_in in parsed_points
    ]
    return fast.Response(json.dumps({"warnings": warnings}), media_type="application/json")

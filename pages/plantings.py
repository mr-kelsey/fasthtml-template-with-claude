from datetime import date

from fasthtml import common as fast

from layout import layout
from farm import parse_optional_int, compute_window
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


def _validate_planting_fields(variety_id, planted_date, quantity, quantity_germinated):
    "Returns (variety_id, planted_date, quantity, quantity_germinated) or an error fast.Response."
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
    return validated_variety_id, planted_date, quantity, quantity_germinated


@router("/plantings", methods=["post"])
def add_planting_route(
    variety_id: str,
    planted_date: str,
    location: str = "",
    quantity: str = "",
    quantity_germinated: str = "",
    notes: str = "",
):
    validated = _validate_planting_fields(variety_id, planted_date, quantity, quantity_germinated)
    if isinstance(validated, fast.Response):
        return validated
    variety_id, planted_date, quantity, quantity_germinated = validated
    db.add_planting(
        variety_id,
        planted_date,
        location=location.strip() or None,
        quantity=quantity,
        quantity_germinated=quantity_germinated,
        notes=notes.strip() or None,
    )
    return fast.Redirect("/plantings")


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
    )


@router("/plantings/{planting_id}/edit", methods=["post"])
def update_planting_route(
    planting_id: int,
    variety_id: str,
    planted_date: str,
    location: str = "",
    quantity: str = "",
    quantity_germinated: str = "",
    notes: str = "",
):
    existing = db.get_planting(planting_id)
    if existing is None:
        return fast.Response("Planting not found.", status_code=404)
    validated = _validate_planting_fields(variety_id, planted_date, quantity, quantity_germinated)
    if isinstance(validated, fast.Response):
        return validated
    variety_id, planted_date, quantity, quantity_germinated = validated
    db.update_planting(
        planting_id,
        variety_id,
        planted_date,
        bed_id=existing["bed_id"],
        location=location.strip() or None,
        quantity=quantity,
        quantity_germinated=quantity_germinated,
        notes=notes.strip() or None,
        cell_x=existing["cell_x"],
        cell_y=existing["cell_y"],
    )
    if existing["bed_id"] is not None:
        return fast.Redirect(f"/beds/{existing['bed_id']}")
    return fast.Redirect("/plantings")


@router("/plantings/{planting_id}/delete", methods=["post"])
def delete_planting_route(planting_id: int):
    planting = db.get_planting(planting_id)
    if planting is None:
        return fast.Redirect("/plantings")
    db.delete_planting(planting_id)
    if planting["bed_id"] is not None:
        return fast.Redirect(f"/beds/{planting['bed_id']}")
    return fast.Redirect("/plantings")


def _cell_assign_form(bed, x, y, varieties):
    "Always blank -- adds a new planting to the cell. Editing an existing one goes through /plantings/{id}/edit."
    return fast.Form(
        fast.Select(
            *[
                fast.Option(f"{variety['common_name']} - {variety['name']}", value=str(variety["id"]))
                for variety in varieties
            ],
            name="variety_id",
            required=True,
        ),
        fast.Input(name="planted_date", type="date", required=True),
        fast.Input(name="quantity", type="number", placeholder="Quantity"),
        fast.Input(name="quantity_germinated", type="number", placeholder="Quantity germinated"),
        fast.Textarea("", name="notes", placeholder="Notes (optional)"),
        fast.Button("Add", type="submit"),
        method="post",
        action=f"/beds/{bed['id']}/cells/{x}/{y}",
    )


def _validate_cell_coordinates(bed, x, y):
    "Returns an error fast.Response when (x, y) falls outside the bed's own grid, else None."
    if not (0 <= x < bed["width_ft"]) or not (0 <= y < bed["length_ft"]):
        return fast.Response("Cell is outside the bed.", status_code=422)
    return None


def _cell_planting_row(planting):
    return fast.Li(
        f"{planting['common_name']} - {planting['variety_name']} (planted {planting['planted_date']})",
        fast.A("Edit", href=f"/plantings/{planting['id']}/edit"),
        fast.Form(
            fast.Button("Delete", type="submit"), method="post", action=f"/plantings/{planting['id']}/delete"
        ),
    )


@router("/beds/{bed_id}/cells/{x}/{y}/edit-fragment", methods=["get"])
def cell_edit_fragment(bed_id: int, x: int, y: int):
    "A cell can hold more than one planting (interplanting), so this lists every occupant plus an add form."
    bed = db.get_bed(bed_id)
    if bed is None:
        return fast.Response("Bed not found.", status_code=404)
    plantings = db.list_plantings_at_cell(bed_id, x, y)
    clear_form = (
        fast.Form(
            fast.Button("Clear cell", type="submit"), method="post", action=f"/beds/{bed_id}/cells/{x}/{y}/clear"
        ),
    ) if plantings else ()
    return (
        fast.H3(f"Cell ({x}, {y})"),
        fast.Ul(*[_cell_planting_row(p) for p in plantings]) if plantings else fast.P("Nothing planted here yet."),
        *clear_form,
        fast.H4("Add a planting"),
        _cell_assign_form(bed, x, y, db.list_seed_varieties()),
        fast.Button("Close", type="button", onclick="document.getElementById('cell-dialog').close()"),
    )


@router("/beds/{bed_id}/cells/{x}/{y}", methods=["post"])
def assign_cell_route(
    bed_id: int,
    x: int,
    y: int,
    variety_id: str,
    planted_date: str,
    quantity: str = "",
    quantity_germinated: str = "",
    notes: str = "",
):
    "Adds a planting to this cell -- a cell can hold more than one (e.g. interplanting)."
    bed = db.get_bed(bed_id)
    if bed is None:
        return fast.Response("Bed not found.", status_code=404)
    coordinate_error = _validate_cell_coordinates(bed, x, y)
    if coordinate_error is not None:
        return coordinate_error
    validated = _validate_planting_fields(variety_id, planted_date, quantity, quantity_germinated)
    if isinstance(validated, fast.Response):
        return validated
    variety_id, planted_date, quantity, quantity_germinated = validated
    db.add_planting(
        variety_id,
        planted_date,
        bed_id=bed_id,
        quantity=quantity,
        quantity_germinated=quantity_germinated,
        notes=notes.strip() or None,
        cell_x=x,
        cell_y=y,
    )
    return fast.Redirect(f"/beds/{bed_id}")


@router("/beds/{bed_id}/cells/{x}/{y}/clear", methods=["post"])
def clear_cell_route(bed_id: int, x: int, y: int):
    "Removes every planting occupying this cell."
    for planting in db.list_plantings_at_cell(bed_id, x, y):
        db.delete_planting(planting["id"])
    return fast.Redirect(f"/beds/{bed_id}")

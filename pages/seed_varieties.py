from fasthtml import common as fast

from layout import layout
from farm import parse_agronomic_fields, format_day_range
import db

router = fast.APIRouter()


def _optional_value(variety, field):
    if variety is None or variety[field] is None:
        return ""
    return variety[field]


def _override_form_fields(variety=None):
    "Blank means 'inherit the plant's default' -- these are the variety's own raw override columns, not effective values."
    return (
        fast.Input(
            name="germination_days_min",
            type="number",
            placeholder="Germination days min (override)",
            value=_optional_value(variety, "germination_days_min"),
        ),
        fast.Input(
            name="germination_days_max",
            type="number",
            placeholder="Germination days max (override)",
            value=_optional_value(variety, "germination_days_max"),
        ),
        fast.Input(
            name="days_to_maturity_min",
            type="number",
            placeholder="Days to maturity min (override)",
            value=_optional_value(variety, "days_to_maturity_min"),
        ),
        fast.Input(
            name="days_to_maturity_max",
            type="number",
            placeholder="Days to maturity max (override)",
            value=_optional_value(variety, "days_to_maturity_max"),
        ),
        fast.Input(
            name="spacing_in",
            type="number",
            placeholder="Spacing in (override)",
            value=_optional_value(variety, "spacing_in"),
        ),
        fast.Input(
            name="sun_needs", placeholder="Sun needs (override)", value=_optional_value(variety, "sun_needs")
        ),
        fast.Input(
            name="water_needs", placeholder="Water needs (override)", value=_optional_value(variety, "water_needs")
        ),
    )


def _variety_form(action, submit_label, plants, variety=None):
    selected_plant_id = variety["plant_id"] if variety else None
    return fast.Form(
        fast.Select(
            *[
                fast.Option(plant["name"], value=str(plant["id"]), selected=(plant["id"] == selected_plant_id))
                for plant in plants
            ],
            name="plant_id",
            required=True,
        ),
        fast.Input(name="name", placeholder="Variety name", value=variety["name"] if variety else "", required=True),
        *_override_form_fields(variety),
        fast.Button(submit_label, type="submit"),
        method="post",
        action=action,
    )


def _variety_row(variety):
    return fast.Tr(
        fast.Td(variety["name"]),
        fast.Td(variety["plant_name"] or ""),
        fast.Td(format_day_range(variety["germination_days_min"], variety["germination_days_max"])),
        fast.Td(format_day_range(variety["days_to_maturity_min"], variety["days_to_maturity_max"])),
        fast.Td(variety["spacing_in"] if variety["spacing_in"] is not None else ""),
        fast.Td(variety["sun_needs"] or ""),
        fast.Td(variety["water_needs"] or ""),
        fast.Td(
            fast.A("Edit", href=f"/seed-varieties/{variety['id']}/edit"),
            fast.Form(
                fast.Button("Delete", type="submit"),
                method="post",
                action=f"/seed-varieties/{variety['id']}/delete",
            ),
        ),
    )


@router("/seed-varieties", methods=["get"])
def list_seed_varieties_page():
    plants = db.list_plants()
    varieties = db.list_seed_varieties()
    headers = ["Name", "Plant", "Germination (days)", "Maturity (days)", "Spacing (in)", "Sun", "Water", ""]
    rows = (
        [_variety_row(v) for v in varieties]
        if varieties
        else [fast.Tr(fast.Td("No seed varieties yet.", colspan=str(len(headers))))]
    )
    table = fast.Table(
        fast.Thead(fast.Tr(*[fast.Th(h) for h in headers])),
        fast.Tbody(*rows),
    )
    add_section = (
        (
            fast.H2("Add a seed variety"),
            fast.P("Blank fields inherit the plant's default -- fill one in only when this cultivar differs."),
            _variety_form(action="/seed-varieties", submit_label="Add Variety", plants=plants),
        )
        if plants
        else (fast.P(fast.A("Add a plant", href="/plants"), " first before adding varieties of it."),)
    )
    return layout(
        "Seed Varieties",
        fast.H1("Seed Varieties"),
        *add_section,
        fast.H2("All varieties"),
        table,
    )


def _validate_plant_id(plant_id: str):
    "Returns the int plant_id if it references an existing plant, or an error fast.Response."
    ok, parsed_plant_id = (True, int(plant_id)) if plant_id.strip().isdigit() else (False, None)
    if not ok or db.get_plant(parsed_plant_id) is None:
        return fast.Response("Choose a valid plant.", status_code=422)
    return parsed_plant_id


@router("/seed-varieties", methods=["post"])
def add_seed_variety_route(
    plant_id: str,
    name: str,
    germination_days_min: str = "",
    germination_days_max: str = "",
    days_to_maturity_min: str = "",
    days_to_maturity_max: str = "",
    spacing_in: str = "",
    sun_needs: str = "",
    water_needs: str = "",
):
    name = name.strip()
    if not name:
        return fast.Response("Name is required.", status_code=422)
    validated_plant_id = _validate_plant_id(plant_id)
    if isinstance(validated_plant_id, fast.Response):
        return validated_plant_id
    fields, error = parse_agronomic_fields(
        germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max, spacing_in
    )
    if error:
        return fast.Response(error, status_code=422)
    db.add_seed_variety(
        validated_plant_id, name, sun_needs=sun_needs.strip() or None, water_needs=water_needs.strip() or None, **fields
    )
    return fast.Redirect("/seed-varieties")


@router("/seed-varieties/{variety_id}/edit", methods=["get"])
def edit_seed_variety_page(variety_id: int):
    variety = db.get_seed_variety(variety_id)
    if variety is None:
        return fast.Response("Seed variety not found.", status_code=404)
    return layout(
        "Edit Seed Variety",
        fast.H1("Edit Seed Variety"),
        _variety_form(
            action=f"/seed-varieties/{variety_id}/edit",
            submit_label="Save Changes",
            plants=db.list_plants(),
            variety=variety,
        ),
    )


@router("/seed-varieties/{variety_id}/edit", methods=["post"])
def update_seed_variety_route(
    variety_id: int,
    plant_id: str,
    name: str,
    germination_days_min: str = "",
    germination_days_max: str = "",
    days_to_maturity_min: str = "",
    days_to_maturity_max: str = "",
    spacing_in: str = "",
    sun_needs: str = "",
    water_needs: str = "",
):
    name = name.strip()
    if not name:
        return fast.Response("Name is required.", status_code=422)
    validated_plant_id = _validate_plant_id(plant_id)
    if isinstance(validated_plant_id, fast.Response):
        return validated_plant_id
    fields, error = parse_agronomic_fields(
        germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max, spacing_in
    )
    if error:
        return fast.Response(error, status_code=422)
    db.update_seed_variety(
        variety_id,
        validated_plant_id,
        name,
        sun_needs=sun_needs.strip() or None,
        water_needs=water_needs.strip() or None,
        **fields,
    )
    return fast.Redirect("/seed-varieties")


@router("/seed-varieties/{variety_id}/delete", methods=["post"])
def delete_seed_variety_route(variety_id: int):
    db.delete_seed_variety(variety_id)
    return fast.Redirect("/seed-varieties")

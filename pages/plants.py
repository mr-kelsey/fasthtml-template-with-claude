from fasthtml import common as fast

from layout import layout
from farm import parse_agronomic_fields, format_day_range
import db

router = fast.APIRouter()


def _optional_value(plant, field):
    if plant is None or plant[field] is None:
        return ""
    return plant[field]


def _agronomic_form_fields(plant=None):
    return (
        fast.Input(name="species", placeholder="Species (optional)", value=_optional_value(plant, "species")),
        fast.Input(
            name="plant_family", placeholder="Plant family (optional)", value=_optional_value(plant, "plant_family")
        ),
        fast.Input(
            name="germination_days_min",
            type="number",
            placeholder="Germination days (min)",
            value=_optional_value(plant, "germination_days_min"),
        ),
        fast.Input(
            name="germination_days_max",
            type="number",
            placeholder="Germination days (max)",
            value=_optional_value(plant, "germination_days_max"),
        ),
        fast.Input(
            name="days_to_maturity_min",
            type="number",
            placeholder="Days to maturity (min)",
            value=_optional_value(plant, "days_to_maturity_min"),
        ),
        fast.Input(
            name="days_to_maturity_max",
            type="number",
            placeholder="Days to maturity (max)",
            value=_optional_value(plant, "days_to_maturity_max"),
        ),
        fast.Input(
            name="spacing_in", type="number", placeholder="Spacing (in)", value=_optional_value(plant, "spacing_in")
        ),
        fast.Input(name="sun_needs", placeholder="Sun needs (optional)", value=_optional_value(plant, "sun_needs")),
        fast.Input(
            name="water_needs", placeholder="Water needs (optional)", value=_optional_value(plant, "water_needs")
        ),
    )


def _plant_form(action, submit_label, plant=None):
    return fast.Form(
        fast.Input(name="name", placeholder="Name", value=plant["name"] if plant else "", required=True),
        *_agronomic_form_fields(plant),
        fast.Button(submit_label, type="submit"),
        method="post",
        action=action,
    )


def _plant_row(plant):
    return fast.Tr(
        fast.Td(plant["name"]),
        fast.Td(plant["species"] or ""),
        fast.Td(plant["plant_family"] or ""),
        fast.Td(format_day_range(plant["germination_days_min"], plant["germination_days_max"])),
        fast.Td(format_day_range(plant["days_to_maturity_min"], plant["days_to_maturity_max"])),
        fast.Td(plant["spacing_in"] if plant["spacing_in"] is not None else ""),
        fast.Td(plant["sun_needs"] or ""),
        fast.Td(plant["water_needs"] or ""),
        fast.Td(
            fast.A("Edit", href=f"/plants/{plant['id']}/edit"),
            fast.Form(
                fast.Button("Delete", type="submit"), method="post", action=f"/plants/{plant['id']}/delete"
            ),
        ),
    )


@router("/plants", methods=["get"])
def list_plants_page():
    plants = db.list_plants()
    headers = ["Name", "Species", "Family", "Germination (days)", "Maturity (days)", "Spacing (in)", "Sun", "Water", ""]
    rows = [_plant_row(p) for p in plants] if plants else [fast.Tr(fast.Td("No plants yet.", colspan=str(len(headers))))]
    table = fast.Table(
        fast.Thead(fast.Tr(*[fast.Th(h) for h in headers])),
        fast.Tbody(*rows),
    )
    return layout(
        "Plants",
        fast.H1("Plants"),
        fast.P("A plant is the crop (e.g. Tomato) and carries default germination/maturity data that varieties can override."),
        fast.H2("Add a plant"),
        _plant_form(action="/plants", submit_label="Add Plant"),
        fast.H2("All plants"),
        table,
    )


@router("/plants", methods=["post"])
def add_plant_route(
    name: str,
    species: str = "",
    plant_family: str = "",
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
    fields, error = parse_agronomic_fields(
        germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max, spacing_in
    )
    if error:
        return fast.Response(error, status_code=422)
    db.add_plant(
        name,
        species=species.strip() or None,
        plant_family=plant_family.strip() or None,
        sun_needs=sun_needs.strip() or None,
        water_needs=water_needs.strip() or None,
        **fields,
    )
    return fast.Redirect("/plants")


@router("/plants/{plant_id}/edit", methods=["get"])
def edit_plant_page(plant_id: int):
    plant = db.get_plant(plant_id)
    if plant is None:
        return fast.Response("Plant not found.", status_code=404)
    return layout(
        "Edit Plant",
        fast.H1("Edit Plant"),
        _plant_form(action=f"/plants/{plant_id}/edit", submit_label="Save Changes", plant=plant),
    )


@router("/plants/{plant_id}/edit", methods=["post"])
def update_plant_route(
    plant_id: int,
    name: str,
    species: str = "",
    plant_family: str = "",
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
    fields, error = parse_agronomic_fields(
        germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max, spacing_in
    )
    if error:
        return fast.Response(error, status_code=422)
    db.update_plant(
        plant_id,
        name,
        species=species.strip() or None,
        plant_family=plant_family.strip() or None,
        sun_needs=sun_needs.strip() or None,
        water_needs=water_needs.strip() or None,
        **fields,
    )
    return fast.Redirect("/plants")


@router("/plants/{plant_id}/delete", methods=["post"])
def delete_plant_route(plant_id: int):
    db.delete_plant(plant_id)
    return fast.Redirect("/plants")

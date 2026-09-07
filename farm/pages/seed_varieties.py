from fasthtml import common as fast

from layout import layout
from farm.helpers import parse_agronomic_fields, format_day_range
import db

router = fast.APIRouter()


def _optional_value(variety, field):
    if variety is None or variety[field] is None:
        return ""
    return variety[field]


def _agronomic_form_fields(variety=None):
    return (
        fast.Input(
            name="germination_days_min",
            type="number",
            placeholder="Germination days (min)",
            value=_optional_value(variety, "germination_days_min"),
        ),
        fast.Input(
            name="germination_days_max",
            type="number",
            placeholder="Germination days (max)",
            value=_optional_value(variety, "germination_days_max"),
        ),
        fast.Input(
            name="days_to_maturity_min",
            type="number",
            placeholder="Days to maturity (min)",
            value=_optional_value(variety, "days_to_maturity_min"),
        ),
        fast.Input(
            name="days_to_maturity_max",
            type="number",
            placeholder="Days to maturity (max)",
            value=_optional_value(variety, "days_to_maturity_max"),
        ),
        fast.Input(
            name="spacing_in", type="number", placeholder="Spacing (in)", value=_optional_value(variety, "spacing_in")
        ),
        fast.Input(name="sun_needs", placeholder="Sun needs (optional)", value=_optional_value(variety, "sun_needs")),
        fast.Input(
            name="water_needs", placeholder="Water needs (optional)", value=_optional_value(variety, "water_needs")
        ),
    )


def _variety_form(action, submit_label, variety=None):
    return fast.Form(
        fast.Input(
            name="common_name",
            placeholder="Common name (e.g. Tomato)",
            value=variety["common_name"] if variety else "",
            required=True,
        ),
        fast.Input(
            name="name", placeholder="Variety name (e.g. Cherokee Purple)", value=variety["name"] if variety else "",
            required=True,
        ),
        fast.Input(
            name="plant_family",
            placeholder="Plant family (e.g. Solanaceae)",
            value=variety["plant_family"] if variety else "",
            required=True,
        ),
        fast.Input(name="genus", placeholder="Genus (optional)", value=_optional_value(variety, "genus")),
        fast.Input(name="species", placeholder="Species (optional)", value=_optional_value(variety, "species")),
        *_agronomic_form_fields(variety),
        fast.Button(submit_label, type="submit"),
        method="post",
        action=action,
    )


def _variety_row(variety):
    return fast.Tr(
        fast.Td(variety["name"]),
        fast.Td(variety["common_name"]),
        fast.Td(variety["plant_family"]),
        fast.Td(variety["genus"] or ""),
        fast.Td(variety["species"] or ""),
        fast.Td(format_day_range(variety["germination_days_min"], variety["germination_days_max"])),
        fast.Td(format_day_range(variety["days_to_maturity_min"], variety["days_to_maturity_max"])),
        fast.Td(variety["spacing_in"] if variety["spacing_in"] is not None else ""),
        fast.Td(variety["sun_needs"] or ""),
        fast.Td(variety["water_needs"] or ""),
        fast.Td(
            fast.A("Edit", href=f"/seed-varieties/{variety['id']}/edit"),
            " ",
            fast.A("Duplicate", href=f"/seed-varieties/{variety['id']}/duplicate"),
            fast.Form(
                fast.Button("Delete", type="submit"),
                method="post",
                action=f"/seed-varieties/{variety['id']}/delete",
            ),
        ),
    )


@router("/seed-varieties", methods=["get"])
def list_seed_varieties_page():
    varieties = db.list_seed_varieties()
    headers = [
        "Variety", "Common Name", "Family", "Genus", "Species",
        "Germination (days)", "Maturity (days)", "Spacing (in)", "Sun", "Water", "",
    ]
    rows = (
        [_variety_row(v) for v in varieties]
        if varieties
        else [fast.Tr(fast.Td("No seed varieties yet.", colspan=str(len(headers))))]
    )
    table = fast.Table(
        fast.Thead(fast.Tr(*[fast.Th(h) for h in headers])),
        fast.Tbody(*rows),
    )
    return layout(
        "Seed Varieties",
        fast.H1("Seed Varieties"),
        fast.H2("Add a seed variety"),
        _variety_form(action="/seed-varieties", submit_label="Add Variety"),
        fast.H2("All varieties"),
        table,
    )


def _validate_required_fields(common_name, name, plant_family):
    "Returns (common_name, name, plant_family) or an error fast.Response."
    common_name = common_name.strip()
    name = name.strip()
    plant_family = plant_family.strip()
    if not common_name or not name or not plant_family:
        return fast.Response("Common name, variety name, and plant family are required.", status_code=422)
    return common_name, name, plant_family


@router("/seed-varieties", methods=["post"])
def add_seed_variety_route(
    common_name: str,
    name: str,
    plant_family: str,
    genus: str = "",
    species: str = "",
    germination_days_min: str = "",
    germination_days_max: str = "",
    days_to_maturity_min: str = "",
    days_to_maturity_max: str = "",
    spacing_in: str = "",
    sun_needs: str = "",
    water_needs: str = "",
):
    validated = _validate_required_fields(common_name, name, plant_family)
    if isinstance(validated, fast.Response):
        return validated
    common_name, name, plant_family = validated
    fields, error = parse_agronomic_fields(
        germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max, spacing_in
    )
    if error:
        return fast.Response(error, status_code=422)
    db.add_seed_variety(
        common_name,
        name,
        plant_family,
        genus=genus.strip() or None,
        species=species.strip() or None,
        sun_needs=sun_needs.strip() or None,
        water_needs=water_needs.strip() or None,
        **fields,
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
        _variety_form(action=f"/seed-varieties/{variety_id}/edit", submit_label="Save Changes", variety=variety),
    )


@router("/seed-varieties/{variety_id}/duplicate", methods=["get"])
def duplicate_seed_variety_page(variety_id: int):
    "Prefills the add form from an existing variety -- posts to the create route, not update, so it makes a new row."
    variety = db.get_seed_variety(variety_id)
    if variety is None:
        return fast.Response("Seed variety not found.", status_code=404)
    return layout(
        "Duplicate Seed Variety",
        fast.H1("Duplicate Seed Variety"),
        fast.P("Edit anything that differs, then save to create a new variety."),
        _variety_form(action="/seed-varieties", submit_label="Add Variety", variety=variety),
    )


@router("/seed-varieties/{variety_id}/edit", methods=["post"])
def update_seed_variety_route(
    variety_id: int,
    common_name: str,
    name: str,
    plant_family: str,
    genus: str = "",
    species: str = "",
    germination_days_min: str = "",
    germination_days_max: str = "",
    days_to_maturity_min: str = "",
    days_to_maturity_max: str = "",
    spacing_in: str = "",
    sun_needs: str = "",
    water_needs: str = "",
):
    validated = _validate_required_fields(common_name, name, plant_family)
    if isinstance(validated, fast.Response):
        return validated
    common_name, name, plant_family = validated
    fields, error = parse_agronomic_fields(
        germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max, spacing_in
    )
    if error:
        return fast.Response(error, status_code=422)
    db.update_seed_variety(
        variety_id,
        common_name,
        name,
        plant_family,
        genus=genus.strip() or None,
        species=species.strip() or None,
        sun_needs=sun_needs.strip() or None,
        water_needs=water_needs.strip() or None,
        **fields,
    )
    return fast.Redirect("/seed-varieties")


@router("/seed-varieties/{variety_id}/delete", methods=["post"])
def delete_seed_variety_route(variety_id: int):
    db.delete_seed_variety(variety_id)
    return fast.Redirect("/seed-varieties")

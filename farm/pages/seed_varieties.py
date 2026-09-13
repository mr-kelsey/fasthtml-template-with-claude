from pathlib import Path
from uuid import uuid4

from fasthtml import common as fast

from farm.layout import layout
from farm.helpers import (
    parse_agronomic_fields,
    parse_soil_feeding_fields,
    validate_sun_needs,
    validate_relation,
    format_day_range,
    format_npk,
    next_palette_color,
    variety_photo_img,
    SUN_NEEDS_OPTIONS,
    RELATION_OPTIONS,
)
import db

router = fast.APIRouter()

PHOTO_ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}
MAX_PHOTO_BYTES = 5 * 1024 * 1024
VARIETY_PHOTO_SUBDIR = "varieties"


def _variety_photos_dir():
    photos_dir = Path(db.UPLOADS_DIR) / VARIETY_PHOTO_SUBDIR
    photos_dir.mkdir(parents=True, exist_ok=True)
    return photos_dir


def _save_uploaded_photo(upload_file):
    "Returns (photo_path, error). photo_path is None (with no error) when no file was chosen."
    if upload_file is None or not upload_file.filename:
        return None, None
    extension = Path(upload_file.filename).suffix.lower().lstrip(".")
    if extension not in PHOTO_ALLOWED_EXTENSIONS:
        return None, f"Photo must be one of: {', '.join(sorted(PHOTO_ALLOWED_EXTENSIONS))}."
    content = upload_file.file.read()
    if not content:
        return None, None
    if len(content) > MAX_PHOTO_BYTES:
        return None, "Photo must be 5MB or smaller."
    _variety_photos_dir()
    relative_path = f"{VARIETY_PHOTO_SUBDIR}/{uuid4().hex}.{extension}"
    (Path(db.UPLOADS_DIR) / relative_path).write_bytes(content)
    return relative_path, None


def _copy_photo(source_relative_path):
    "Physically copies an existing variety photo to a new file, so the new row owns an independent copy."
    source = Path(db.UPLOADS_DIR) / source_relative_path
    if not source.exists():
        return None
    extension = source.suffix.lstrip(".")
    _variety_photos_dir()
    relative_path = f"{VARIETY_PHOTO_SUBDIR}/{uuid4().hex}.{extension}"
    (Path(db.UPLOADS_DIR) / relative_path).write_bytes(source.read_bytes())
    return relative_path


def _delete_photo_file(relative_path):
    if not relative_path:
        return
    (Path(db.UPLOADS_DIR) / relative_path).unlink(missing_ok=True)


def _optional_value(variety, field):
    if variety is None or variety[field] is None:
        return ""
    return variety[field]


def _npk_value(variety, prefix):
    if variety is None:
        return ""
    return format_npk(variety[f"{prefix}_npk_n"], variety[f"{prefix}_npk_p"], variety[f"{prefix}_npk_k"])


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
        fast.Select(
            fast.Option("Sun needs (optional)", value="", selected=_optional_value(variety, "sun_needs") == ""),
            *[
                fast.Option(sun_needs, value=sun_needs, selected=_optional_value(variety, "sun_needs") == sun_needs)
                for sun_needs in SUN_NEEDS_OPTIONS
            ],
            name="sun_needs",
        ),
        fast.Input(
            name="water_needs", placeholder="Water needs (optional)", value=_optional_value(variety, "water_needs")
        ),
        fast.Input(name="soil_type", placeholder="Soil type (optional)", value=_optional_value(variety, "soil_type")),
        fast.Input(
            name="soil_ph_min", type="number", step="0.1", placeholder="Soil pH (min)",
            value=_optional_value(variety, "soil_ph_min"),
        ),
        fast.Input(
            name="soil_ph_max", type="number", step="0.1", placeholder="Soil pH (max)",
            value=_optional_value(variety, "soil_ph_max"),
        ),
        fast.Input(
            name="feeding_frequency_days", type="number", placeholder="Feeding frequency (days)",
            value=_optional_value(variety, "feeding_frequency_days"),
        ),
        fast.Input(
            name="growth_npk", placeholder="Growth cycle food requirements: N-P-K (e.g. 10-5-5)",
            value=_npk_value(variety, "growth"),
        ),
        fast.Input(
            name="produce_npk", placeholder="Produce cycle food requirements: N-P-K (e.g. 5-10-10)",
            value=_npk_value(variety, "produce"),
        ),
    )


def _photo_field(variety, is_edit):
    """Renders the photo upload input, plus whatever context applies: a thumbnail and "remove photo"
    checkbox when editing an existing photo, or a thumbnail and hidden carry-forward field when
    duplicating (photo_path is copied server-side on submit -- see _copy_photo)."""
    upload_input = fast.Input(name="photo", type="file", accept="image/jpeg,image/png,image/webp,image/gif")
    current_photo = variety_photo_img(variety) if variety else None
    if current_photo is None:
        return (fast.Label("Reference photo (optional, for telling seedlings apart from weeds)", upload_input),)
    if is_edit:
        return (
            fast.Div(
                current_photo,
                fast.Label(fast.Input(type="checkbox", name="remove_photo"), " Remove photo"),
            ),
            fast.Label("Replace photo", upload_input),
        )
    return (
        fast.Div(current_photo, fast.P("Photo will be carried over to the new variety unless you pick a new one.")),
        fast.Input(type="hidden", name="duplicate_photo_path", value=variety["photo_path"]),
        fast.Label("Replace photo", upload_input),
    )


def _variety_form(action, submit_label, variety=None, default_color_hex=None, is_edit=False):
    color_value = (variety["color_hex"] if variety else None) or default_color_hex or "#000000"
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
        fast.Label("Color (used for staged/planted dots on the bed detail map)", fast.Input(name="color_hex", type="color", value=color_value)),
        *_photo_field(variety, is_edit),
        *_agronomic_form_fields(variety),
        fast.Button(submit_label, type="submit"),
        method="post",
        action=action,
        enctype="multipart/form-data",
    )


def _variety_row(variety):
    identity_children = []
    photo = variety_photo_img(variety)
    if photo is not None:
        identity_children.append(photo)
    identity_children += [
        fast.Div(
            fast.Span(cls="variety-swatch", style=f"background-color:{variety['color_hex'] or '#888888'}"),
            variety["common_name"],
            cls="variety-identity-name",
        ),
        fast.Div(variety["name"], cls="variety-identity-subtitle"),
    ]
    return fast.Tr(
        fast.Td(*identity_children, cls="sticky-col-left"),
        fast.Td(variety["plant_family"]),
        fast.Td(variety["genus"] or ""),
        fast.Td(variety["species"] or ""),
        fast.Td(format_day_range(variety["germination_days_min"], variety["germination_days_max"])),
        fast.Td(format_day_range(variety["days_to_maturity_min"], variety["days_to_maturity_max"])),
        fast.Td(variety["spacing_in"] if variety["spacing_in"] is not None else ""),
        fast.Td(variety["sun_needs"] or ""),
        fast.Td(variety["water_needs"] or ""),
        fast.Td(variety["soil_type"] or ""),
        fast.Td(variety["soil_ph_min"] if variety["soil_ph_min"] is not None else ""),
        fast.Td(variety["soil_ph_max"] if variety["soil_ph_max"] is not None else ""),
        fast.Td(variety["feeding_frequency_days"] if variety["feeding_frequency_days"] is not None else ""),
        fast.Td(_npk_value(variety, "growth")),
        fast.Td(_npk_value(variety, "produce")),
        fast.Td(
            fast.A("Edit", href=f"/seed-varieties/{variety['id']}/edit"),
            " ",
            fast.A("Duplicate", href=f"/seed-varieties/{variety['id']}/duplicate"),
            fast.Form(
                fast.Button("Delete", type="submit"),
                method="post",
                action=f"/seed-varieties/{variety['id']}/delete",
            ),
            cls="sticky-col",
        ),
    )


def _common_name_select(name, common_names):
    return fast.Select(
        fast.Option("Choose a plant", value="", selected=True),
        *[fast.Option(common_name, value=common_name) for common_name in common_names],
        name=name,
        required=True,
    )


def _companion_rule_form(common_names):
    return fast.Form(
        _common_name_select("plant_a_common_name", common_names),
        _common_name_select("plant_b_common_name", common_names),
        fast.Select(
            fast.Option("Relation", value="", selected=True),
            *[fast.Option(relation, value=relation) for relation in RELATION_OPTIONS],
            name="relation",
        ),
        fast.Input(name="notes", placeholder="Notes (optional)"),
        fast.Button("Add Rule", type="submit"),
        method="post",
        action="/companion-rules",
    )


def _companion_rule_row(rule):
    return fast.Tr(
        fast.Td(rule["plant_a_common_name"]),
        fast.Td(rule["plant_b_common_name"]),
        fast.Td(rule["relation"]),
        fast.Td(rule["notes"] or ""),
        fast.Td(
            fast.Form(
                fast.Button("Delete", type="submit"),
                method="post",
                action=f"/companion-rules/{rule['id']}/delete",
            )
        ),
    )


@router("/seed-varieties", methods=["get"])
def list_seed_varieties_page():
    varieties = db.list_seed_varieties()
    headers = [
        "Variety", "Family", "Genus", "Species",
        "Germination (days)", "Maturity (days)", "Spacing (in)", "Sun", "Water",
        "Soil", "pH Min", "pH Max", "Feed Freq (days)", "Growth N-P-K", "Produce N-P-K", "",
    ]
    rows = (
        [_variety_row(v) for v in varieties]
        if varieties
        else [fast.Tr(fast.Td("No seed varieties yet.", colspan=str(len(headers))))]
    )

    def _header_cls(i):
        if i == 0:
            return "sticky-col-left"
        if i == len(headers) - 1:
            return "sticky-col"
        return None

    header_cells = [fast.Th(h, cls=_header_cls(i)) for i, h in enumerate(headers)]
    table = fast.Div(
        fast.Table(
            fast.Thead(fast.Tr(*header_cells)),
            fast.Tbody(*rows),
        ),
        cls="table-scroll",
    )
    common_names = list(dict.fromkeys(v["common_name"] for v in varieties))
    rules = db.list_companion_rules()
    rule_headers = ["Plant A", "Plant B", "Relation", "Notes", ""]
    rule_rows = (
        [_companion_rule_row(r) for r in rules]
        if rules
        else [fast.Tr(fast.Td("No companion/antagonist rules yet.", colspan=str(len(rule_headers))))]
    )
    rule_table = fast.Table(
        fast.Thead(fast.Tr(*[fast.Th(h) for h in rule_headers])),
        fast.Tbody(*rule_rows),
    )
    return layout(
        "Seed Varieties",
        fast.H1("Seed Varieties"),
        fast.H2("Add a seed variety"),
        _variety_form(action="/seed-varieties", submit_label="Add Variety", default_color_hex=next_palette_color(varieties)),
        fast.H2("All varieties"),
        table,
        fast.H2("Companion / Antagonist Rules"),
        _companion_rule_form(common_names),
        rule_table,
    )


def _validate_required_fields(common_name, name, plant_family):
    "Returns (common_name, name, plant_family) or an error fast.Response."
    common_name = common_name.strip()
    name = name.strip()
    plant_family = plant_family.strip()
    if not common_name or not name or not plant_family:
        return fast.Response("Common name, variety name, and plant family are required.", status_code=422)
    return common_name, name, plant_family


def _validate_soil_feeding_and_sun(
    soil_type, soil_ph_min, soil_ph_max, feeding_frequency_days, growth_npk, produce_npk, sun_needs
):
    "Returns (soil_feeding_fields_dict, sun_needs_value_or_none) or an error fast.Response."
    soil_feeding_fields, error = parse_soil_feeding_fields(
        soil_type, soil_ph_min, soil_ph_max, feeding_frequency_days, growth_npk, produce_npk
    )
    if error:
        return fast.Response(error, status_code=422)
    sun_needs_value, error = validate_sun_needs(sun_needs)
    if error:
        return fast.Response(error, status_code=422)
    return soil_feeding_fields, sun_needs_value


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
    soil_type: str = "",
    soil_ph_min: str = "",
    soil_ph_max: str = "",
    feeding_frequency_days: str = "",
    growth_npk: str = "",
    produce_npk: str = "",
    color_hex: str = "",
    photo: fast.UploadFile = None,
    duplicate_photo_path: str = "",
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
    validated_soil = _validate_soil_feeding_and_sun(
        soil_type, soil_ph_min, soil_ph_max, feeding_frequency_days, growth_npk, produce_npk, sun_needs
    )
    if isinstance(validated_soil, fast.Response):
        return validated_soil
    soil_feeding_fields, sun_needs_value = validated_soil
    photo_path, error = _save_uploaded_photo(photo)
    if error:
        return fast.Response(error, status_code=422)
    if photo_path is None and duplicate_photo_path.strip():
        photo_path = _copy_photo(duplicate_photo_path.strip())
    db.add_seed_variety(
        common_name,
        name,
        plant_family,
        genus=genus.strip() or None,
        species=species.strip() or None,
        sun_needs=sun_needs_value,
        water_needs=water_needs.strip() or None,
        color_hex=color_hex.strip() or None,
        photo_path=photo_path,
        **fields,
        **soil_feeding_fields,
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
            action=f"/seed-varieties/{variety_id}/edit", submit_label="Save Changes", variety=variety, is_edit=True
        ),
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
    soil_type: str = "",
    soil_ph_min: str = "",
    soil_ph_max: str = "",
    feeding_frequency_days: str = "",
    growth_npk: str = "",
    produce_npk: str = "",
    color_hex: str = "",
    photo: fast.UploadFile = None,
    remove_photo: str = "",
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
    validated_soil = _validate_soil_feeding_and_sun(
        soil_type, soil_ph_min, soil_ph_max, feeding_frequency_days, growth_npk, produce_npk, sun_needs
    )
    if isinstance(validated_soil, fast.Response):
        return validated_soil
    soil_feeding_fields, sun_needs_value = validated_soil
    existing = db.get_seed_variety(variety_id)
    existing_photo_path = existing["photo_path"] if existing else None
    new_photo_path, error = _save_uploaded_photo(photo)
    if error:
        return fast.Response(error, status_code=422)
    if new_photo_path is not None:
        _delete_photo_file(existing_photo_path)
        photo_path = new_photo_path
    elif remove_photo.strip():
        _delete_photo_file(existing_photo_path)
        photo_path = None
    else:
        photo_path = existing_photo_path
    db.update_seed_variety(
        variety_id,
        common_name,
        name,
        plant_family,
        genus=genus.strip() or None,
        species=species.strip() or None,
        sun_needs=sun_needs_value,
        water_needs=water_needs.strip() or None,
        color_hex=color_hex.strip() or None,
        photo_path=photo_path,
        **fields,
        **soil_feeding_fields,
    )
    return fast.Redirect("/seed-varieties")


@router("/seed-varieties/{variety_id}/delete", methods=["post"])
def delete_seed_variety_route(variety_id: int):
    variety = db.get_seed_variety(variety_id)
    db.delete_seed_variety(variety_id)
    if variety is not None:
        _delete_photo_file(variety["photo_path"])
    return fast.Redirect("/seed-varieties")


@router("/companion-rules", methods=["post"])
def add_companion_rule_route(plant_a_common_name: str, plant_b_common_name: str, relation: str, notes: str = ""):
    plant_a_common_name = plant_a_common_name.strip()
    plant_b_common_name = plant_b_common_name.strip()
    if not plant_a_common_name or not plant_b_common_name:
        return fast.Response("Both plant common names are required.", status_code=422)
    relation_value, error = validate_relation(relation)
    if error:
        return fast.Response(error, status_code=422)
    db.add_companion_rule(plant_a_common_name, plant_b_common_name, relation_value, notes=notes.strip() or None)
    return fast.Redirect("/seed-varieties")


@router("/companion-rules/{rule_id}/delete", methods=["post"])
def delete_companion_rule_route(rule_id: int):
    db.delete_companion_rule(rule_id)
    return fast.Redirect("/seed-varieties")

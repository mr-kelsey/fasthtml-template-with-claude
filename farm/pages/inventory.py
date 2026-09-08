from fasthtml import common as fast

from farm.layout import layout
from farm.helpers import parse_optional_int, parse_optional_date
import db

router = fast.APIRouter()


def _optional_value(row, field):
    if row is None or row[field] is None:
        return ""
    return row[field]


def _variety_label(variety):
    return f"{variety['common_name']} - {variety['name']}"


def _variety_select(varieties, selected_id=None):
    return fast.Select(
        *[
            fast.Option(_variety_label(v), value=str(v["id"]), selected=(v["id"] == selected_id))
            for v in varieties
        ],
        name="variety_id",
        required=True,
    )


def _planting_label(planting):
    return f"{planting['common_name']} - {planting['variety_name']} planted {planting['planted_date']} (#{planting['id']})"


def _origin_planting_select(plantings, selected_id=None):
    return fast.Select(
        fast.Option("No origin (purchased)", value="", selected=selected_id is None),
        *[
            fast.Option(_planting_label(p), value=str(p["id"]), selected=(p["id"] == selected_id))
            for p in plantings
        ],
        name="origin_planting_id",
    )


def _seed_lot_form(action, submit_label, varieties=None, lot=None):
    "Variety is set once at creation (varieties given) and immutable afterward (varieties omitted on edit)."
    variety_field = (_variety_select(varieties),) if varieties is not None else ()
    return fast.Form(
        *variety_field,
        fast.Input(
            name="quantity_on_hand", type="number", placeholder="Quantity on hand",
            value=_optional_value(lot, "quantity_on_hand"),
        ),
        fast.Input(
            name="acquired_date", type="date", placeholder="Acquired date", value=_optional_value(lot, "acquired_date")
        ),
        fast.Input(name="seed_source", placeholder="Seed source (optional)", value=_optional_value(lot, "seed_source")),
        fast.Textarea(lot["notes"] or "" if lot else "", name="notes", placeholder="Notes (optional)"),
        fast.Button(submit_label, type="submit"),
        method="post",
        action=action,
    )


def _seed_lot_row(lot):
    return fast.Tr(
        fast.Td(f"{lot['common_name']} - {lot['variety_name']}"),
        fast.Td(lot["quantity_on_hand"] if lot["quantity_on_hand"] is not None else ""),
        fast.Td(lot["acquired_date"] or ""),
        fast.Td(lot["seed_source"] or ""),
        fast.Td(lot["notes"] or ""),
        fast.Td(
            fast.A("Edit", href=f"/seed-lots/{lot['id']}/edit"),
            fast.Form(fast.Button("Delete", type="submit"), method="post", action=f"/seed-lots/{lot['id']}/delete"),
        ),
    )


def _transplant_lot_form(action, submit_label, plantings, varieties=None, lot=None):
    "Variety is set once at creation (varieties given) and immutable afterward (varieties omitted on edit)."
    variety_field = (_variety_select(varieties),) if varieties is not None else ()
    return fast.Form(
        *variety_field,
        fast.Input(
            name="quantity_on_hand", type="number", placeholder="Quantity on hand",
            value=_optional_value(lot, "quantity_on_hand"),
        ),
        _origin_planting_select(plantings, selected_id=lot["origin_planting_id"] if lot else None),
        fast.Input(
            name="purchased_source", placeholder="Purchased source (optional)",
            value=_optional_value(lot, "purchased_source"),
        ),
        fast.Input(
            name="purchased_vendor", placeholder="Purchased vendor (optional)",
            value=_optional_value(lot, "purchased_vendor"),
        ),
        fast.Input(
            name="purchased_date", type="date", placeholder="Purchased date",
            value=_optional_value(lot, "purchased_date"),
        ),
        fast.Textarea(lot["notes"] or "" if lot else "", name="notes", placeholder="Notes (optional)"),
        fast.Button(submit_label, type="submit"),
        method="post",
        action=action,
    )


def _transplant_lot_row(lot):
    return fast.Tr(
        fast.Td(f"{lot['common_name']} - {lot['variety_name']}"),
        fast.Td(lot["quantity_on_hand"] if lot["quantity_on_hand"] is not None else ""),
        fast.Td(lot["origin_planting_id"] if lot["origin_planting_id"] is not None else ""),
        fast.Td(lot["purchased_source"] or ""),
        fast.Td(lot["purchased_vendor"] or ""),
        fast.Td(lot["purchased_date"] or ""),
        fast.Td(lot["notes"] or ""),
        fast.Td(
            fast.A("Edit", href=f"/transplant-lots/{lot['id']}/edit"),
            fast.Form(
                fast.Button("Delete", type="submit"), method="post", action=f"/transplant-lots/{lot['id']}/delete"
            ),
        ),
    )


@router("/inventory", methods=["get"])
def inventory_page():
    varieties = db.list_seed_varieties()
    plantings = db.list_plantings()
    seed_lots = db.list_seed_lots()
    transplant_lots = db.list_transplant_lots()

    seed_headers = ["Variety", "Qty on hand", "Acquired", "Source", "Notes", ""]
    seed_rows = (
        [_seed_lot_row(lot) for lot in seed_lots]
        if seed_lots
        else [fast.Tr(fast.Td("No seed lots yet.", colspan=str(len(seed_headers))))]
    )
    seed_table = fast.Table(fast.Thead(fast.Tr(*[fast.Th(h) for h in seed_headers])), fast.Tbody(*seed_rows))

    transplant_headers = [
        "Variety", "Qty on hand", "Origin planting", "Purchased source", "Vendor", "Purchased", "Notes", "",
    ]
    transplant_rows = (
        [_transplant_lot_row(lot) for lot in transplant_lots]
        if transplant_lots
        else [fast.Tr(fast.Td("No transplant lots yet.", colspan=str(len(transplant_headers))))]
    )
    transplant_table = fast.Table(
        fast.Thead(fast.Tr(*[fast.Th(h) for h in transplant_headers])), fast.Tbody(*transplant_rows)
    )

    seed_add_section = (
        (_seed_lot_form(action="/seed-lots", submit_label="Add Seed Lot", varieties=varieties),)
        if varieties
        else (fast.P(fast.A("Add a seed variety", href="/seed-varieties"), " first before tracking seed inventory."),)
    )
    transplant_add_section = (
        (
            _transplant_lot_form(
                action="/transplant-lots", submit_label="Add Transplant Lot", varieties=varieties, plantings=plantings
            ),
        )
        if varieties
        else (
            fast.P(fast.A("Add a seed variety", href="/seed-varieties"), " first before tracking transplant inventory."),
        )
    )

    return layout(
        "Inventory",
        fast.H1("Inventory"),
        fast.H2("Seed Lots"),
        *seed_add_section,
        seed_table,
        fast.H2("Transplant Lots"),
        *transplant_add_section,
        transplant_table,
    )


def _validate_variety_id(variety_id: str):
    "Returns the int variety_id if it references an existing seed variety, or an error fast.Response."
    ok, parsed = (True, int(variety_id)) if variety_id.strip().isdigit() else (False, None)
    if not ok or db.get_seed_variety(parsed) is None:
        return fast.Response("Choose a valid seed variety.", status_code=422)
    return parsed


def _validate_optional_planting_id(planting_id: str):
    "Returns (int_or_none, None) or (None, error_message)."
    if planting_id is None or planting_id.strip() == "":
        return None, None
    if not planting_id.strip().isdigit() or db.get_planting(int(planting_id)) is None:
        return None, "Choose a valid origin planting."
    return int(planting_id), None


@router("/seed-lots", methods=["post"])
def add_seed_lot_route(
    variety_id: str,
    quantity_on_hand: str = "",
    acquired_date: str = "",
    seed_source: str = "",
    notes: str = "",
):
    validated_variety_id = _validate_variety_id(variety_id)
    if isinstance(validated_variety_id, fast.Response):
        return validated_variety_id
    ok, quantity_on_hand = parse_optional_int(quantity_on_hand)
    if not ok:
        return fast.Response("Quantity on hand must be a number.", status_code=422)
    ok, acquired_date = parse_optional_date(acquired_date)
    if not ok:
        return fast.Response("Acquired date must be a valid date.", status_code=422)
    db.add_seed_lot(
        validated_variety_id, quantity_on_hand=quantity_on_hand, acquired_date=acquired_date,
        seed_source=seed_source.strip() or None, notes=notes.strip() or None,
    )
    return fast.Redirect("/inventory")


@router("/seed-lots/{seed_lot_id}/edit", methods=["get"])
def edit_seed_lot_page(seed_lot_id: int):
    lot = db.get_seed_lot(seed_lot_id)
    if lot is None:
        return fast.Response("Seed lot not found.", status_code=404)
    variety = db.get_seed_variety(lot["variety_id"])
    return layout(
        "Edit Seed Lot",
        fast.H1("Edit Seed Lot"),
        fast.P(fast.Strong("Variety: "), _variety_label(variety) if variety else "Unknown"),
        _seed_lot_form(action=f"/seed-lots/{seed_lot_id}/edit", submit_label="Save Changes", lot=lot),
    )


@router("/seed-lots/{seed_lot_id}/edit", methods=["post"])
def update_seed_lot_route(
    seed_lot_id: int,
    quantity_on_hand: str = "",
    acquired_date: str = "",
    seed_source: str = "",
    notes: str = "",
):
    if db.get_seed_lot(seed_lot_id) is None:
        return fast.Response("Seed lot not found.", status_code=404)
    ok, quantity_on_hand = parse_optional_int(quantity_on_hand)
    if not ok:
        return fast.Response("Quantity on hand must be a number.", status_code=422)
    ok, acquired_date = parse_optional_date(acquired_date)
    if not ok:
        return fast.Response("Acquired date must be a valid date.", status_code=422)
    db.update_seed_lot(
        seed_lot_id, quantity_on_hand=quantity_on_hand, acquired_date=acquired_date,
        seed_source=seed_source.strip() or None, notes=notes.strip() or None,
    )
    return fast.Redirect("/inventory")


@router("/seed-lots/{seed_lot_id}/delete", methods=["post"])
def delete_seed_lot_route(seed_lot_id: int):
    db.delete_seed_lot(seed_lot_id)
    return fast.Redirect("/inventory")


@router("/transplant-lots", methods=["post"])
def add_transplant_lot_route(
    variety_id: str,
    quantity_on_hand: str = "",
    origin_planting_id: str = "",
    purchased_source: str = "",
    purchased_vendor: str = "",
    purchased_date: str = "",
    notes: str = "",
):
    validated_variety_id = _validate_variety_id(variety_id)
    if isinstance(validated_variety_id, fast.Response):
        return validated_variety_id
    ok, quantity_on_hand = parse_optional_int(quantity_on_hand)
    if not ok:
        return fast.Response("Quantity on hand must be a number.", status_code=422)
    validated_origin_id, error = _validate_optional_planting_id(origin_planting_id)
    if error:
        return fast.Response(error, status_code=422)
    ok, purchased_date = parse_optional_date(purchased_date)
    if not ok:
        return fast.Response("Purchased date must be a valid date.", status_code=422)
    db.add_transplant_lot(
        validated_variety_id, quantity_on_hand=quantity_on_hand, origin_planting_id=validated_origin_id,
        purchased_source=purchased_source.strip() or None, purchased_vendor=purchased_vendor.strip() or None,
        purchased_date=purchased_date, notes=notes.strip() or None,
    )
    return fast.Redirect("/inventory")


@router("/transplant-lots/{transplant_lot_id}/edit", methods=["get"])
def edit_transplant_lot_page(transplant_lot_id: int):
    lot = db.get_transplant_lot(transplant_lot_id)
    if lot is None:
        return fast.Response("Transplant lot not found.", status_code=404)
    variety = db.get_seed_variety(lot["variety_id"])
    return layout(
        "Edit Transplant Lot",
        fast.H1("Edit Transplant Lot"),
        fast.P(fast.Strong("Variety: "), _variety_label(variety) if variety else "Unknown"),
        _transplant_lot_form(
            action=f"/transplant-lots/{transplant_lot_id}/edit", submit_label="Save Changes",
            plantings=db.list_plantings(), lot=lot,
        ),
    )


@router("/transplant-lots/{transplant_lot_id}/edit", methods=["post"])
def update_transplant_lot_route(
    transplant_lot_id: int,
    quantity_on_hand: str = "",
    origin_planting_id: str = "",
    purchased_source: str = "",
    purchased_vendor: str = "",
    purchased_date: str = "",
    notes: str = "",
):
    if db.get_transplant_lot(transplant_lot_id) is None:
        return fast.Response("Transplant lot not found.", status_code=404)
    ok, quantity_on_hand = parse_optional_int(quantity_on_hand)
    if not ok:
        return fast.Response("Quantity on hand must be a number.", status_code=422)
    validated_origin_id, error = _validate_optional_planting_id(origin_planting_id)
    if error:
        return fast.Response(error, status_code=422)
    ok, purchased_date = parse_optional_date(purchased_date)
    if not ok:
        return fast.Response("Purchased date must be a valid date.", status_code=422)
    db.update_transplant_lot(
        transplant_lot_id, quantity_on_hand=quantity_on_hand, origin_planting_id=validated_origin_id,
        purchased_source=purchased_source.strip() or None, purchased_vendor=purchased_vendor.strip() or None,
        purchased_date=purchased_date, notes=notes.strip() or None,
    )
    return fast.Redirect("/inventory")


@router("/transplant-lots/{transplant_lot_id}/delete", methods=["post"])
def delete_transplant_lot_route(transplant_lot_id: int):
    db.delete_transplant_lot(transplant_lot_id)
    return fast.Redirect("/inventory")


@router("/transplant-lots/{transplant_lot_id}/quantity", methods=["post"])
def update_transplant_lot_quantity_route(transplant_lot_id: int, quantity_on_hand: str):
    "Single-field inline update -- the bed-detail palette's armed-variety row edits quantity live via fetch()."
    if db.get_transplant_lot(transplant_lot_id) is None:
        return fast.Response("Transplant lot not found.", status_code=404)
    ok, quantity = parse_optional_int(quantity_on_hand)
    if not ok or quantity is None or quantity < 0:
        return fast.Response("Quantity on hand must be a non-negative number.", status_code=422)
    db.update_transplant_lot_quantity(transplant_lot_id, quantity)
    return fast.Response(status_code=204)


@router("/transplant-lots/{transplant_lot_id}/plantings", methods=["get"])
def transplant_lot_plantings_page(transplant_lot_id: int):
    "The lot side of phase 5's lineage view -- every bed-planting drawn from this lot."
    lot = db.get_transplant_lot(transplant_lot_id)
    if lot is None:
        return fast.Response("Transplant lot not found.", status_code=404)
    variety = db.get_seed_variety(lot["variety_id"])
    plantings = db.list_plantings_by_transplant_lot(transplant_lot_id)
    headers = ["Bed", "Planted", ""]
    rows = (
        [
            fast.Tr(
                fast.Td(str(p["bed_id"]) if p["bed_id"] is not None else ""),
                fast.Td(p["planted_date"]),
                fast.Td(fast.A("View", href=f"/plantings/{p['id']}/edit")),
            )
            for p in plantings
        ]
        if plantings
        else [fast.Tr(fast.Td("No plantings drawn from this lot yet.", colspan=str(len(headers))))]
    )
    return layout(
        "Transplant Lot Plantings",
        fast.H1(f"Plantings from lot: {_variety_label(variety) if variety else 'Unknown'}"),
        fast.Table(fast.Thead(fast.Tr(*[fast.Th(h) for h in headers])), fast.Tbody(*rows)),
    )

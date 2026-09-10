from fasthtml import common as fast

from farm.layout import layout
from farm.helpers import (
    parse_optional_int,
    parse_optional_float,
    parse_optional_date,
    parse_npk_formula,
    format_npk,
)
import db

router = fast.APIRouter()


def _optional_value(row, field):
    if row is None or row[field] is None:
        return ""
    return row[field]


def _product_form(action, submit_label, product=None):
    npk_value = format_npk(product["npk_n"], product["npk_p"], product["npk_k"]) if product else ""
    return fast.Form(
        fast.Input(
            name="name", placeholder="Product name (e.g. Fish Emulsion)", value=product["name"] if product else "",
            required=True,
        ),
        fast.Input(
            name="product_type", placeholder="Type (e.g. fertilizer, pesticide, fungicide, soap)",
            value=_optional_value(product, "product_type"),
        ),
        fast.Input(name="npk", placeholder="NPK formula (optional, e.g. 5-1-1)", value=npk_value),
        fast.Textarea(
            product["benefit_notes"] or "" if product else "", name="benefit_notes",
            placeholder="What is this for? (optional)",
        ),
        fast.Input(
            name="application_frequency_days", type="number", placeholder="Reapply every (days)",
            value=_optional_value(product, "application_frequency_days"),
        ),
        fast.Button(submit_label, type="submit"),
        method="post",
        action=action,
    )


def _product_row(product):
    return fast.Tr(
        fast.Td(product["name"]),
        fast.Td(product["product_type"] or ""),
        fast.Td(format_npk(product["npk_n"], product["npk_p"], product["npk_k"])),
        fast.Td(product["benefit_notes"] or ""),
        fast.Td(
            product["application_frequency_days"] if product["application_frequency_days"] is not None else ""
        ),
        fast.Td(
            fast.A("Edit", href=f"/garden-products/{product['id']}/edit"),
            fast.Form(
                fast.Button("Delete", type="submit"), method="post",
                action=f"/garden-products/{product['id']}/delete",
            ),
        ),
    )


def _product_select(products, selected_id=None):
    return fast.Select(
        *[
            fast.Option(product["name"], value=str(product["id"]), selected=(product["id"] == selected_id))
            for product in products
        ],
        name="product_id",
        required=True,
    )


def _bed_label(bed):
    return f"{bed['plot_name']} / {bed['label']}"


def _bed_select(beds, selected_id=None):
    return fast.Select(
        fast.Option("— no bed (use location) —", value="", selected=selected_id is None),
        *[
            fast.Option(_bed_label(bed), value=str(bed["id"]), selected=(bed["id"] == selected_id))
            for bed in beds
        ],
        name="bed_id",
    )


def _application_form(action, submit_label, products, beds, application=None):
    return fast.Form(
        _product_select(products, selected_id=application["product_id"] if application else None),
        fast.Input(
            name="applied_date", type="date", value=application["applied_date"] if application else "",
            required=True,
        ),
        _bed_select(beds, selected_id=application["bed_id"] if application else None),
        fast.Input(
            name="location", placeholder="Location (optional, e.g. north fence row)",
            value=(application["location"] or "") if application else "",
        ),
        fast.Input(
            name="amount", type="number", step="0.1", placeholder="Amount",
            value=_optional_value(application, "amount"),
        ),
        fast.Input(name="unit", placeholder="Unit (e.g. cups, gal, oz)", value=_optional_value(application, "unit")),
        fast.Textarea(
            application["notes"] or "" if application else "", name="notes", placeholder="Notes (optional)"
        ),
        fast.Button(submit_label, type="submit"),
        method="post",
        action=action,
    )


def _application_target_label(application):
    if application["bed_id"] is not None:
        return f"{application['plot_name']} / {application['bed_label']}" if application["plot_name"] else str(application["bed_id"])
    return application["location"] or ""


def _application_row(application):
    return fast.Tr(
        fast.Td(application["product_name"] or ""),
        fast.Td(application["applied_date"]),
        fast.Td(_application_target_label(application)),
        fast.Td(application["amount"] if application["amount"] is not None else ""),
        fast.Td(application["unit"] or ""),
        fast.Td(application["notes"] or ""),
        fast.Td(
            fast.A("Edit", href=f"/product-applications/{application['id']}/edit"),
            fast.Form(
                fast.Button("Delete", type="submit"), method="post",
                action=f"/product-applications/{application['id']}/delete",
            ),
        ),
    )


@router("/products", methods=["get"])
def products_page():
    products = db.list_garden_products()
    applications = db.list_product_applications()
    beds = db.list_beds()

    product_headers = ["Name", "Type", "NPK", "Benefit", "Reapply (days)", ""]
    product_rows = (
        [_product_row(p) for p in products]
        if products
        else [fast.Tr(fast.Td("No garden products yet.", colspan=str(len(product_headers))))]
    )
    product_table = fast.Table(fast.Thead(fast.Tr(*[fast.Th(h) for h in product_headers])), fast.Tbody(*product_rows))

    application_headers = ["Product", "Applied", "Target", "Amount", "Unit", "Notes", ""]
    application_rows = (
        [_application_row(a) for a in applications]
        if applications
        else [fast.Tr(fast.Td("No product applications yet.", colspan=str(len(application_headers))))]
    )
    application_table = fast.Table(
        fast.Thead(fast.Tr(*[fast.Th(h) for h in application_headers])), fast.Tbody(*application_rows)
    )

    application_add_section = (
        (
            _application_form(
                action="/product-applications", submit_label="Log Application", products=products, beds=beds
            ),
        )
        if products
        else (fast.P(fast.A("Add a garden product", href="#garden-products-form"), " first before logging applications."),)
    )

    return layout(
        "Products",
        fast.H1("Garden Products"),
        fast.H2("Add a garden product", id="garden-products-form"),
        _product_form(action="/garden-products", submit_label="Add Product"),
        fast.H2("All products"),
        product_table,
        fast.H2("Product Applications"),
        *application_add_section,
        application_table,
    )


def _validate_name(name: str):
    "Returns the stripped name or an error fast.Response."
    name = name.strip()
    if not name:
        return fast.Response("Name is required.", status_code=422)
    return name


def _parse_product_fields(product_type, npk, benefit_notes, application_frequency_days):
    "Returns (fields_dict, None) or (None, error_message)."
    ok, (npk_n, npk_p, npk_k) = parse_npk_formula(npk)
    if not ok:
        return None, "NPK must be in N-P-K format (e.g. 5-1-1)."
    ok, frequency = parse_optional_int(application_frequency_days)
    if not ok:
        return None, "Reapply frequency must be a number."
    return {
        "product_type": product_type.strip() or None,
        "npk_n": npk_n, "npk_p": npk_p, "npk_k": npk_k,
        "benefit_notes": benefit_notes.strip() or None,
        "application_frequency_days": frequency,
    }, None


@router("/garden-products", methods=["post"])
def add_garden_product_route(
    name: str,
    product_type: str = "",
    npk: str = "",
    benefit_notes: str = "",
    application_frequency_days: str = "",
):
    validated_name = _validate_name(name)
    if isinstance(validated_name, fast.Response):
        return validated_name
    fields, error = _parse_product_fields(product_type, npk, benefit_notes, application_frequency_days)
    if error:
        return fast.Response(error, status_code=422)
    db.add_garden_product(validated_name, **fields)
    return fast.Redirect("/products")


@router("/garden-products/{product_id}/edit", methods=["get"])
def edit_garden_product_page(product_id: int):
    product = db.get_garden_product(product_id)
    if product is None:
        return fast.Response("Garden product not found.", status_code=404)
    return layout(
        "Edit Garden Product",
        fast.H1("Edit Garden Product"),
        _product_form(action=f"/garden-products/{product_id}/edit", submit_label="Save Changes", product=product),
    )


@router("/garden-products/{product_id}/edit", methods=["post"])
def update_garden_product_route(
    product_id: int,
    name: str,
    product_type: str = "",
    npk: str = "",
    benefit_notes: str = "",
    application_frequency_days: str = "",
):
    validated_name = _validate_name(name)
    if isinstance(validated_name, fast.Response):
        return validated_name
    fields, error = _parse_product_fields(product_type, npk, benefit_notes, application_frequency_days)
    if error:
        return fast.Response(error, status_code=422)
    db.update_garden_product(product_id, validated_name, **fields)
    return fast.Redirect("/products")


@router("/garden-products/{product_id}/delete", methods=["post"])
def delete_garden_product_route(product_id: int):
    db.delete_garden_product(product_id)
    return fast.Redirect("/products")


def _validate_product_id(product_id: str):
    "Returns the int product_id if it references an existing garden product, or an error fast.Response."
    ok, parsed = (True, int(product_id)) if product_id.strip().isdigit() else (False, None)
    if not ok or db.get_garden_product(parsed) is None:
        return fast.Response("Choose a valid garden product.", status_code=422)
    return parsed


def _validate_applied_date(applied_date: str):
    "Returns the stripped applied_date or an error fast.Response."
    applied_date = applied_date.strip()
    ok, parsed = parse_optional_date(applied_date)
    if not applied_date or not ok:
        return fast.Response("Invalid applied date.", status_code=422)
    return parsed


def _validate_optional_bed_id(bed_id: str):
    "Returns (int_or_none, None) or (None, error_message)."
    if bed_id is None or bed_id.strip() == "":
        return None, None
    if not bed_id.strip().isdigit() or db.get_bed(int(bed_id)) is None:
        return None, "Choose a valid bed."
    return int(bed_id), None


def _target_fields(bed_id: str, location: str):
    "A bed selection wins over free-text location. Returns (bed_id_or_none, location_or_none) or an error fast.Response."
    validated_bed_id, error = _validate_optional_bed_id(bed_id)
    if error:
        return fast.Response(error, status_code=422)
    if validated_bed_id is not None:
        return validated_bed_id, None
    return None, location.strip() or None


@router("/product-applications", methods=["post"])
def add_product_application_route(
    product_id: str,
    applied_date: str,
    bed_id: str = "",
    location: str = "",
    amount: str = "",
    unit: str = "",
    notes: str = "",
):
    validated_product_id = _validate_product_id(product_id)
    if isinstance(validated_product_id, fast.Response):
        return validated_product_id
    validated_date = _validate_applied_date(applied_date)
    if isinstance(validated_date, fast.Response):
        return validated_date
    target = _target_fields(bed_id, location)
    if isinstance(target, fast.Response):
        return target
    validated_bed_id, validated_location = target
    ok, amount_value = parse_optional_float(amount)
    if not ok:
        return fast.Response("Amount must be a number.", status_code=422)
    db.add_product_application(
        validated_product_id, validated_date, bed_id=validated_bed_id, location=validated_location,
        amount=amount_value, unit=unit.strip() or None, notes=notes.strip() or None,
    )
    return fast.Redirect("/products")


@router("/product-applications/{application_id}/edit", methods=["get"])
def edit_product_application_page(application_id: int):
    application = db.get_product_application(application_id)
    if application is None:
        return fast.Response("Product application not found.", status_code=404)
    return layout(
        "Edit Product Application",
        fast.H1("Edit Product Application"),
        _application_form(
            action=f"/product-applications/{application_id}/edit", submit_label="Save Changes",
            products=db.list_garden_products(), beds=db.list_beds(), application=application,
        ),
    )


@router("/product-applications/{application_id}/edit", methods=["post"])
def update_product_application_route(
    application_id: int,
    product_id: str,
    applied_date: str,
    bed_id: str = "",
    location: str = "",
    amount: str = "",
    unit: str = "",
    notes: str = "",
):
    if db.get_product_application(application_id) is None:
        return fast.Response("Product application not found.", status_code=404)
    validated_product_id = _validate_product_id(product_id)
    if isinstance(validated_product_id, fast.Response):
        return validated_product_id
    validated_date = _validate_applied_date(applied_date)
    if isinstance(validated_date, fast.Response):
        return validated_date
    target = _target_fields(bed_id, location)
    if isinstance(target, fast.Response):
        return target
    validated_bed_id, validated_location = target
    ok, amount_value = parse_optional_float(amount)
    if not ok:
        return fast.Response("Amount must be a number.", status_code=422)
    db.update_product_application(
        application_id, validated_product_id, validated_date, bed_id=validated_bed_id, location=validated_location,
        amount=amount_value, unit=unit.strip() or None, notes=notes.strip() or None,
    )
    return fast.Redirect("/products")


@router("/product-applications/{application_id}/delete", methods=["post"])
def delete_product_application_route(application_id: int):
    db.delete_product_application(application_id)
    return fast.Redirect("/products")

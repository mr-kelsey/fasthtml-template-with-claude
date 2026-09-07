from fasthtml import common as fast
from fasthtml.svg import Svg, Rect, G, Text

from layout import layout
from farm import parse_required_int, parse_optional_int
import db

router = fast.APIRouter()


def _optional_value(row, field):
    if row is None or row[field] is None:
        return ""
    return row[field]


def _plot_form(action, submit_label, plot=None):
    return fast.Form(
        fast.Input(name="name", placeholder="Name", value=plot["name"] if plot else "", required=True),
        fast.Input(
            name="width_ft", type="number", placeholder="Width (ft)",
            value=plot["width_ft"] if plot else "", required=True,
        ),
        fast.Input(
            name="height_ft", type="number", placeholder="Height (ft)",
            value=plot["height_ft"] if plot else "", required=True,
        ),
        fast.Button(submit_label, type="submit"),
        method="post",
        action=action,
    )


def _plot_row(plot):
    return fast.Tr(
        fast.Td(fast.A(plot["name"], href=f"/land-plots/{plot['id']}/map")),
        fast.Td(f"{plot['width_ft']} x {plot['height_ft']} ft"),
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


def _validate_plot_fields(name, width_ft, height_ft):
    "Returns (name, width_ft, height_ft) or an error fast.Response."
    name = name.strip()
    if not name:
        return fast.Response("Name is required.", status_code=422)
    width_ft, error = parse_required_int(width_ft, "Width")
    if error:
        return fast.Response(error, status_code=422)
    height_ft, error = parse_required_int(height_ft, "Height")
    if error:
        return fast.Response(error, status_code=422)
    return name, width_ft, height_ft


@router("/land-plots", methods=["post"])
def add_land_plot_route(name: str, width_ft: str, height_ft: str):
    validated = _validate_plot_fields(name, width_ft, height_ft)
    if isinstance(validated, fast.Response):
        return validated
    name, width_ft, height_ft = validated
    db.add_land_plot(name, width_ft, height_ft)
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
def update_land_plot_route(plot_id: int, name: str, width_ft: str, height_ft: str):
    validated = _validate_plot_fields(name, width_ft, height_ft)
    if isinstance(validated, fast.Response):
        return validated
    name, width_ft, height_ft = validated
    db.update_land_plot(plot_id, name, width_ft, height_ft)
    return fast.Redirect("/land-plots")


@router("/land-plots/{plot_id}/delete", methods=["post"])
def delete_land_plot_route(plot_id: int):
    db.delete_land_plot(plot_id)
    return fast.Redirect("/land-plots")


def _add_bed_form(plot_id):
    return fast.Form(
        fast.Input(name="label", placeholder="Label (e.g. Bed 1)", required=True),
        fast.Input(name="width_ft", type="number", placeholder="Width (ft)", required=True),
        fast.Input(name="height_ft", type="number", placeholder="Height (ft)", required=True),
        fast.Input(name="sun_exposure", placeholder="Sun exposure (optional)"),
        fast.Input(name="irrigation_zone", placeholder="Irrigation zone (optional)"),
        fast.Button("Add Bed", type="submit"),
        method="post",
        action=f"/land-plots/{plot_id}/beds",
    )


def _unplaced_bed_item(bed):
    return fast.Li(
        f"{bed['label']} ({bed['width_ft']} x {bed['height_ft']} ft)",
        fast.Form(
            fast.Button("Add to map", type="submit"), method="post", action=f"/beds/{bed['id']}/place"
        ),
        cls="unplaced-bed-item",
    )


def _bed_group(bed):
    x, y = bed["x"], bed["y"]
    center_x, center_y = bed["width_ft"] / 2, bed["height_ft"] / 2
    return G(
        Rect(bed["width_ft"], bed["height_ft"], cls="bed-rect"),
        Text(bed["label"], x=center_x, y=center_y, text_anchor="middle", dominant_baseline="middle", cls="bed-label"),
        Rect(1, 1, x=bed["width_ft"] - 1, y=bed["height_ft"] - 1, cls="resize-handle"),
        id=f"bed-{bed['id']}",
        cls="bed-group",
        transform=f"translate({x},{y}) rotate({bed['rotation_deg']},{center_x},{center_y})",
        hx_get=f"/beds/{bed['id']}/edit-fragment",
        hx_target="#bed-dialog-body",
        hx_trigger="click",
        hx_on__after_request="document.getElementById('bed-dialog').showModal()",
    )


@router("/land-plots/{plot_id}/map", methods=["get"])
def land_plot_map_page(plot_id: int):
    plot = db.get_land_plot(plot_id)
    if plot is None:
        return fast.Response("Land plot not found.", status_code=404)
    beds = db.list_beds_for_plot(plot_id)
    placed_beds = [b for b in beds if b["x"] is not None and b["y"] is not None]
    unplaced_beds = [b for b in beds if b["x"] is None or b["y"] is None]
    canvas = Svg(
        *[_bed_group(bed) for bed in placed_beds],
        viewBox=f"0 0 {plot['width_ft']} {plot['height_ft']}",
        cls="land-map-svg",
        id="land-map-svg",
        data_plot_width=str(plot["width_ft"]),
        data_plot_height=str(plot["height_ft"]),
    )
    sidebar = fast.Div(
        fast.H2("Unplaced beds"),
        fast.Ul(*[_unplaced_bed_item(b) for b in unplaced_beds]) if unplaced_beds else fast.P("None."),
        fast.H2("Add a bed"),
        _add_bed_form(plot_id),
        cls="land-map-sidebar",
    )
    return layout(
        f"{plot['name']} Map",
        fast.H1(f"{plot['name']} ({plot['width_ft']} x {plot['height_ft']} ft)"),
        fast.A("All plots", href="/land-plots"),
        fast.Div(canvas, sidebar, cls="land-map-layout"),
        fast.Dialog(fast.Div(id="bed-dialog-body"), id="bed-dialog"),
        fast.Script(src="/land-map.js"),
    )


def _validate_bed_dimensions(width_ft, height_ft):
    "Returns (width_ft, height_ft) or an error fast.Response."
    width_ft, error = parse_required_int(width_ft, "Width")
    if error:
        return fast.Response(error, status_code=422)
    height_ft, error = parse_required_int(height_ft, "Height")
    if error:
        return fast.Response(error, status_code=422)
    return width_ft, height_ft


@router("/land-plots/{plot_id}/beds", methods=["post"])
def add_bed_route(
    plot_id: int,
    label: str,
    width_ft: str,
    height_ft: str,
    sun_exposure: str = "",
    irrigation_zone: str = "",
):
    label = label.strip()
    if not label:
        return fast.Response("Label is required.", status_code=422)
    validated = _validate_bed_dimensions(width_ft, height_ft)
    if isinstance(validated, fast.Response):
        return validated
    width_ft, height_ft = validated
    db.add_bed(
        plot_id, label, width_ft, height_ft,
        sun_exposure=sun_exposure.strip() or None, irrigation_zone=irrigation_zone.strip() or None,
    )
    return fast.Redirect(f"/land-plots/{plot_id}/map")


@router("/beds/{bed_id}/position", methods=["post"])
def update_bed_position_route(bed_id: int, x: str, y: str):
    x, error = parse_required_int(x, "X")
    if error:
        return fast.Response(error, status_code=422)
    y, error = parse_required_int(y, "Y")
    if error:
        return fast.Response(error, status_code=422)
    db.update_bed_position(bed_id, x, y)
    return fast.Response(status_code=204)


@router("/beds/{bed_id}/place", methods=["post"])
def place_bed_route(bed_id: int):
    "Moves an unplaced bed onto the map at a default position -- the plain-form counterpart to /position (JS drag)."
    bed = db.get_bed(bed_id)
    if bed is None:
        return fast.Response("Bed not found.", status_code=404)
    db.update_bed_position(bed_id, 0, 0)
    return fast.Redirect(f"/land-plots/{bed['plot_id']}/map")


@router("/beds/{bed_id}/size", methods=["post"])
def update_bed_size_route(bed_id: int, width_ft: str, height_ft: str):
    validated = _validate_bed_dimensions(width_ft, height_ft)
    if isinstance(validated, fast.Response):
        return validated
    width_ft, height_ft = validated
    db.update_bed_size(bed_id, max(1, width_ft), max(1, height_ft))
    return fast.Response(status_code=204)


def _bed_edit_form(bed):
    return fast.Form(
        fast.Input(name="label", placeholder="Label", value=bed["label"], required=True),
        fast.Input(name="width_ft", type="number", placeholder="Width (ft)", value=bed["width_ft"], required=True),
        fast.Input(name="height_ft", type="number", placeholder="Height (ft)", value=bed["height_ft"], required=True),
        fast.Input(
            name="rotation_deg", type="number", placeholder="Rotation (degrees)", value=bed["rotation_deg"],
            min="0", max="359",
        ),
        fast.Input(name="sun_exposure", placeholder="Sun exposure (optional)", value=_optional_value(bed, "sun_exposure")),
        fast.Input(
            name="irrigation_zone", placeholder="Irrigation zone (optional)",
            value=_optional_value(bed, "irrigation_zone"),
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
def update_bed_route(
    bed_id: int,
    label: str,
    width_ft: str,
    height_ft: str,
    rotation_deg: str = "",
    sun_exposure: str = "",
    irrigation_zone: str = "",
):
    bed = db.get_bed(bed_id)
    if bed is None:
        return fast.Response("Bed not found.", status_code=404)
    label = label.strip()
    if not label:
        return fast.Response("Label is required.", status_code=422)
    validated = _validate_bed_dimensions(width_ft, height_ft)
    if isinstance(validated, fast.Response):
        return validated
    width_ft, height_ft = validated
    ok, rotation_deg = parse_optional_int(rotation_deg)
    if not ok:
        return fast.Response("Rotation must be a number.", status_code=422)
    db.update_bed(
        bed_id, label, width_ft, height_ft, rotation_deg or 0,
        sun_exposure=sun_exposure.strip() or None, irrigation_zone=irrigation_zone.strip() or None,
    )
    return fast.Redirect(f"/land-plots/{bed['plot_id']}/map")


@router("/beds/{bed_id}/delete", methods=["post"])
def delete_bed_route(bed_id: int):
    bed = db.get_bed(bed_id)
    if bed is None:
        return fast.Redirect("/land-plots")
    db.delete_bed(bed_id)
    return fast.Redirect(f"/land-plots/{bed['plot_id']}/map")

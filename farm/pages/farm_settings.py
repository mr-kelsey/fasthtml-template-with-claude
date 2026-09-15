from fasthtml import common as fast

from farm.layout import layout
from farm.helpers import parse_optional_date
import db

router = fast.APIRouter()


def _optional_value(settings, field):
    return settings[field] if settings[field] is not None else ""


def _farm_settings_form(settings):
    return fast.Form(
        fast.Label(
            "Average last spring frost (used for frost-risk warnings and cover-crop reminders)",
            fast.Input(name="last_frost_date", type="date", value=_optional_value(settings, "last_frost_date")),
        ),
        fast.Label(
            "Average first fall frost",
            fast.Input(name="first_frost_date", type="date", value=_optional_value(settings, "first_frost_date")),
        ),
        fast.Button("Save", type="submit"),
        method="post",
        action="/farm-settings",
    )


@router("/farm-settings", methods=["get"])
def farm_settings_page():
    settings = db.get_farm_settings()
    return layout(
        "Farm Settings",
        fast.H1("Farm Settings"),
        _farm_settings_form(settings),
    )


@router("/farm-settings", methods=["post"])
def update_farm_settings_route(last_frost_date: str = "", first_frost_date: str = ""):
    ok, parsed_last_frost = parse_optional_date(last_frost_date)
    if not ok:
        return fast.Response("Last frost date must be a valid date.", status_code=422)
    ok, parsed_first_frost = parse_optional_date(first_frost_date)
    if not ok:
        return fast.Response("First frost date must be a valid date.", status_code=422)
    db.update_farm_settings(last_frost_date=parsed_last_frost, first_frost_date=parsed_first_frost)
    return fast.Redirect("/farm-settings")

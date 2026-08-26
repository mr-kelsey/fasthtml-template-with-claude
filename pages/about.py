from fasthtml import common as fast
from layout import layout

router = fast.APIRouter()


@router("/about", methods=["get"])
def about_page():
    return layout(
        "About",
        fast.H1("About"),
        fast.P("This template demonstrates multipage FastHTML routing with a SQLite-backed CRUD demo."),
        fast.P("Routes live in ", fast.Code("pages/"), ", persistence lives in ", fast.Code("db.py"), "."),
    )

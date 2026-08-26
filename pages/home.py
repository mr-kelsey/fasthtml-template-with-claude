from fasthtml import common as fast
from layout import layout

router = fast.APIRouter()


@router("/", methods=["get"])
def home_page():
    return layout(
        "Home",
        fast.H1("Welcome"),
        fast.P("A FastHTML + SQLite starter template."),
        fast.P("See the ", fast.A("Notes", href="/notes"), " page for a working SQLite CRUD example."),
    )

from fasthtml import common as fast

from db import init_db, UPLOADS_DIR
from pages import discover_page_modules
from farm.pages import discover_page_modules as discover_farm_page_modules

app, _ = fast.fast_app(
    title="FastHTML Template",
    on_startup=[init_db],
)
# Registered in this order because Starlette matches routes by registration order, not specificity:
# the catch-all static route below (prefix "/") would otherwise shadow "/uploads/..." requests too.
app.static_route_exts(prefix="/uploads/", static_path=UPLOADS_DIR)
app.static_route_exts(static_path="static")

for page_module in discover_page_modules():
    page_module.router.to_app(app)

for page_module in discover_farm_page_modules():
    page_module.router.to_app(app)

fast.serve()

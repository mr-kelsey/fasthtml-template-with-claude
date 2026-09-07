from fasthtml import common as fast

from db import init_db
from pages import discover_page_modules
from farm.pages import discover_page_modules as discover_farm_page_modules

app, _ = fast.fast_app(
    title="FastHTML Template",
    static_path="static",
    on_startup=[init_db],
)

for page_module in discover_page_modules():
    page_module.router.to_app(app)

for page_module in discover_farm_page_modules():
    page_module.router.to_app(app)

fast.serve()

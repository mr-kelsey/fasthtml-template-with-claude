import socket
import threading
import time

import pytest
import uvicorn
from playwright.sync_api import sync_playwright
from sqlalchemy import text

import db
from main import app as _live_app


# Child-before-parent delete order, so a table is always emptied before whatever it FKs to:
# farm_events/harvests -> plantings -> seed_lots/transplant_lots -> seed_varieties;
# product_applications -> garden_products; shade_polygons -> shade_sources -> beds -> land_plots;
# companion_rules has no FK to any other farm table.
_FARM_TABLES = (
    "farm_events", "product_applications", "garden_products", "harvests", "plantings",
    "companion_rules", "seed_lots", "transplant_lots", "seed_varieties",
    "shade_polygons", "shade_sources", "beds", "land_plots",
)


@pytest.fixture(autouse=True)
def _clean_farm_tables():
    "Start and end each test with every farm table empty, in the isolated test database (.env.test)."
    with db.engine.begin() as db_connection:
        for table in _FARM_TABLES:
            db_connection.execute(text(f"DELETE FROM {table}"))
    yield
    with db.engine.begin() as db_connection:
        for table in _FARM_TABLES:
            db_connection.execute(text(f"DELETE FROM {table}"))


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server_url():
    "Runs the real app under uvicorn in a background thread, for JS tests that need a real HTTP server for Playwright to load pages from -- TestClient's ASGI transport has no URL a browser can navigate to. Shares the same db.engine (.env.test) already swapped in by tests/conftest.py, so the per-test table-cleanup fixtures above still apply to writes made over HTTP."
    config = uvicorn.Config(_live_app, host="127.0.0.1", port=_free_port(), log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{config.port}"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as playwright:
        chromium = playwright.chromium.launch()
        yield chromium
        chromium.close()


@pytest.fixture
def page(browser):
    browser_page = browser.new_page()
    yield browser_page
    browser_page.close()

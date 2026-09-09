import socket
import threading
import time

import pytest
import uvicorn
from playwright.sync_api import sync_playwright
from sqlalchemy import text

import db
from main import app as _live_app


@pytest.fixture(autouse=True)
def _clean_farm_events():
    "Start and end each test with an empty farm_events table (cleaned before plantings, its parent)."
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM farm_events"))
    yield
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM farm_events"))


@pytest.fixture(autouse=True)
def _clean_plantings():
    "Start and end each test with an empty plantings table (cleaned before seed_varieties/plants, its parents)."
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM plantings"))
    yield
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM plantings"))


@pytest.fixture(autouse=True)
def _clean_companion_rules():
    "Start and end each test with an empty companion_rules table (no FK to any other farm table)."
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM companion_rules"))
    yield
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM companion_rules"))


@pytest.fixture(autouse=True)
def _clean_seed_lots():
    "Start and end each test with an empty seed_lots table (cleaned before seed_varieties, its parent)."
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM seed_lots"))
    yield
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM seed_lots"))


@pytest.fixture(autouse=True)
def _clean_transplant_lots():
    "Start and end each test with an empty transplant_lots table (cleaned before seed_varieties/plantings, its parents)."
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM transplant_lots"))
    yield
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM transplant_lots"))


@pytest.fixture(autouse=True)
def _clean_seed_varieties():
    "Start and end each test with an empty seed_varieties table in the isolated test database (.env.test)."
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM seed_varieties"))
    yield
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM seed_varieties"))


@pytest.fixture(autouse=True)
def _clean_beds():
    "Start and end each test with an empty beds table (cleaned before land_plots, its parent)."
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM beds"))
    yield
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM beds"))


@pytest.fixture(autouse=True)
def _clean_land_plots():
    "Start and end each test with an empty land_plots table in the isolated test database (.env.test)."
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM land_plots"))
    yield
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM land_plots"))


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

import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

import db

# Point db's shared instance at the isolated test database (.env.test) before importing
# main/pages below — they call db.<name> at request time, so this must run first.
db._instance = db.Database(".env.test")

from main import app  # noqa: E402 -- must import after the db swap above


@pytest.fixture(scope="session", autouse=True)
def _schema():
    "Ensure the notes table exists before any test runs."
    db.init_db()


@pytest.fixture(autouse=True)
def _clean_notes():
    "Start and end each test with an empty notes table in the isolated test database (.env.test)."
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM notes"))
    yield
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM notes"))


@pytest.fixture(autouse=True)
def _clean_calendar_events():
    "Start and end each test with an empty calendar_events table in the isolated test database (.env.test)."
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM calendar_events"))
    yield
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM calendar_events"))


@pytest.fixture(autouse=True)
def _clean_recurring_events():
    "Start and end each test with an empty recurring_events table in the isolated test database (.env.test)."
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM recurring_events"))
    yield
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM recurring_events"))


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


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

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


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

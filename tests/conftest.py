import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

import db
from main import app


@pytest.fixture(scope="session", autouse=True)
def _schema():
    "Ensure the notes table exists before any test runs."
    db.init_db()


@pytest.fixture(autouse=True)
def _clean_notes():
    "Tests share the database configured in .env — start and end each test with an empty notes table."
    with db.engine.begin() as conn:
        conn.execute(text("DELETE FROM notes"))
    yield
    with db.engine.begin() as conn:
        conn.execute(text("DELETE FROM notes"))


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

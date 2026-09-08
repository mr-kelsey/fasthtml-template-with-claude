import pytest
from sqlalchemy import text

import db


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
def _clean_seed_lots():
    "Start and end each test with an empty seed_lots table (cleaned before seed_varieties, its parent)."
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM seed_lots"))
    yield
    with db.engine.begin() as db_connection:
        db_connection.execute(text("DELETE FROM seed_lots"))


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

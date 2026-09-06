from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS calendar_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id TEXT NOT NULL,
        title TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        start_time TEXT,
        end_time TEXT,
        notes TEXT,
        is_critical INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS recurring_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        month INTEGER NOT NULL,
        day INTEGER NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS plants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        species TEXT,
        plant_family TEXT,
        germination_days_min INTEGER,
        germination_days_max INTEGER,
        days_to_maturity_min INTEGER,
        days_to_maturity_max INTEGER,
        spacing_in INTEGER,
        sun_needs TEXT,
        water_needs TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS seed_varieties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plant_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        germination_days_min INTEGER,
        germination_days_max INTEGER,
        days_to_maturity_min INTEGER,
        days_to_maturity_max INTEGER,
        spacing_in INTEGER,
        sun_needs TEXT,
        water_needs TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS plantings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        variety_id INTEGER NOT NULL,
        bed_id INTEGER,
        location TEXT,
        planted_date TEXT NOT NULL,
        quantity INTEGER,
        quantity_germinated INTEGER,
        notes TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
]

_EVENT_COLUMNS = (
    "id, owner_id, title, start_date, end_date, start_time, end_time, notes, is_critical, created_at"
)

_RECURRING_EVENT_COLUMNS = "id, title, month, day, created_at"

_AGRONOMIC_COLUMNS = (
    "germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max, "
    "spacing_in, sun_needs, water_needs"
)

_PLANT_COLUMNS = f"id, name, species, plant_family, {_AGRONOMIC_COLUMNS}, created_at"

_SEED_VARIETY_COLUMNS = f"id, plant_id, name, {_AGRONOMIC_COLUMNS}, created_at"

_PLANTING_COLUMNS = (
    "id, variety_id, bed_id, location, planted_date, quantity, quantity_germinated, notes, created_at"
)


def _agronomic_fields(
    germination_days_min: int,
    germination_days_max: int,
    days_to_maturity_min: int,
    days_to_maturity_max: int,
    spacing_in: int,
    sun_needs: str,
    water_needs: str,
):
    "Shared by plants and seed_varieties, which carry the same agronomic columns (variety values override plant defaults)."
    return {
        "germination_days_min": germination_days_min,
        "germination_days_max": germination_days_max,
        "days_to_maturity_min": days_to_maturity_min,
        "days_to_maturity_max": days_to_maturity_max,
        "spacing_in": spacing_in,
        "sun_needs": sun_needs or None,
        "water_needs": water_needs or None,
    }


class Database:
    "Owns one SQLite engine, built from the given dotenv file. Tests build their own instance from .env.test."

    def __init__(self, env_file=".env"):
        env = dotenv_values(env_file)
        self.DB_PATH = env.get("DB_PATH", "data/app.db")
        self._engine = None

    @property
    def engine(self):
        if self._engine is None:
            Path(self.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
            self._engine = create_engine(f"sqlite:///{self.DB_PATH}", connect_args={"check_same_thread": False})
        return self._engine

    def init_db(self):
        with self.engine.begin() as db_connection:
            for statement in SCHEMA_STATEMENTS:
                db_connection.execute(text(statement))

    def list_notes(self):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text("SELECT id, title, body, created_at FROM notes ORDER BY created_at DESC, id DESC")
            ).mappings().all()

    def add_note(self, title: str, body: str):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text("INSERT INTO notes (title, body) VALUES (:title, :body)"),
                {"title": title, "body": body},
            )

    def delete_note(self, note_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM notes WHERE id = :id"), {"id": note_id})

    def list_events(self):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_EVENT_COLUMNS} FROM calendar_events ORDER BY start_date, start_time")
            ).mappings().all()

    def list_events_in_range(self, range_start: str, range_end: str, owner_id: str = None):
        "Events whose [start_date, end_date] overlaps [range_start, range_end], inclusive."
        query = (
            f"SELECT {_EVENT_COLUMNS} FROM calendar_events "
            "WHERE start_date <= :range_end AND end_date >= :range_start"
        )
        params = {"range_start": range_start, "range_end": range_end}
        if owner_id:
            query += " AND owner_id = :owner_id"
            params["owner_id"] = owner_id
        query += " ORDER BY start_date, start_time"
        with self.engine.connect() as db_connection:
            return db_connection.execute(text(query), params).mappings().all()

    def get_event(self, event_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_EVENT_COLUMNS} FROM calendar_events WHERE id = :id"),
                {"id": event_id},
            ).mappings().first()

    @staticmethod
    def _normalize_event_fields(title, start_date, end_date, start_time, end_time, notes, is_critical):
        return {
            "title": title,
            "start_date": start_date,
            "end_date": end_date or start_date,
            "start_time": start_time or None,
            "end_time": end_time or None,
            "notes": notes or None,
            "is_critical": int(bool(is_critical)),
        }

    def add_event(
        self,
        owner_id: str,
        title: str,
        start_date: str,
        end_date: str,
        start_time: str,
        end_time: str,
        notes: str,
        is_critical: bool,
    ):
        fields = self._normalize_event_fields(title, start_date, end_date, start_time, end_time, notes, is_critical)
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "INSERT INTO calendar_events "
                    "(owner_id, title, start_date, end_date, start_time, end_time, notes, is_critical) "
                    "VALUES (:owner_id, :title, :start_date, :end_date, :start_time, :end_time, :notes, :is_critical)"
                ),
                {"owner_id": owner_id, **fields},
            )

    def update_event(
        self,
        event_id: int,
        title: str,
        start_date: str,
        end_date: str,
        start_time: str,
        end_time: str,
        notes: str,
        is_critical: bool,
    ):
        fields = self._normalize_event_fields(title, start_date, end_date, start_time, end_time, notes, is_critical)
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "UPDATE calendar_events SET title = :title, start_date = :start_date, "
                    "end_date = :end_date, start_time = :start_time, end_time = :end_time, "
                    "notes = :notes, is_critical = :is_critical WHERE id = :id"
                ),
                {"id": event_id, **fields},
            )

    def delete_event(self, event_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM calendar_events WHERE id = :id"), {"id": event_id})

    def list_recurring_events(self):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_RECURRING_EVENT_COLUMNS} FROM recurring_events ORDER BY month, day")
            ).mappings().all()

    def get_recurring_event(self, event_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_RECURRING_EVENT_COLUMNS} FROM recurring_events WHERE id = :id"),
                {"id": event_id},
            ).mappings().first()

    def add_recurring_event(self, title: str, month: int, day: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text("INSERT INTO recurring_events (title, month, day) VALUES (:title, :month, :day)"),
                {"title": title, "month": month, "day": day},
            )

    def update_recurring_event(self, event_id: int, title: str, month: int, day: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "UPDATE recurring_events SET title = :title, month = :month, day = :day WHERE id = :id"
                ),
                {"id": event_id, "title": title, "month": month, "day": day},
            )

    def delete_recurring_event(self, event_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM recurring_events WHERE id = :id"), {"id": event_id})

    def list_plants(self):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_PLANT_COLUMNS} FROM plants ORDER BY name")
            ).mappings().all()

    def get_plant(self, plant_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_PLANT_COLUMNS} FROM plants WHERE id = :id"), {"id": plant_id}
            ).mappings().first()

    def add_plant(
        self,
        name: str,
        species: str = None,
        plant_family: str = None,
        germination_days_min: int = None,
        germination_days_max: int = None,
        days_to_maturity_min: int = None,
        days_to_maturity_max: int = None,
        spacing_in: int = None,
        sun_needs: str = None,
        water_needs: str = None,
    ):
        fields = _agronomic_fields(
            germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max,
            spacing_in, sun_needs, water_needs,
        )
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "INSERT INTO plants (name, species, plant_family, germination_days_min, germination_days_max, "
                    "days_to_maturity_min, days_to_maturity_max, spacing_in, sun_needs, water_needs) "
                    "VALUES (:name, :species, :plant_family, :germination_days_min, :germination_days_max, "
                    ":days_to_maturity_min, :days_to_maturity_max, :spacing_in, :sun_needs, :water_needs)"
                ),
                {"name": name, "species": species or None, "plant_family": plant_family or None, **fields},
            )

    def update_plant(
        self,
        plant_id: int,
        name: str,
        species: str = None,
        plant_family: str = None,
        germination_days_min: int = None,
        germination_days_max: int = None,
        days_to_maturity_min: int = None,
        days_to_maturity_max: int = None,
        spacing_in: int = None,
        sun_needs: str = None,
        water_needs: str = None,
    ):
        fields = _agronomic_fields(
            germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max,
            spacing_in, sun_needs, water_needs,
        )
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "UPDATE plants SET name = :name, species = :species, plant_family = :plant_family, "
                    "germination_days_min = :germination_days_min, germination_days_max = :germination_days_max, "
                    "days_to_maturity_min = :days_to_maturity_min, days_to_maturity_max = :days_to_maturity_max, "
                    "spacing_in = :spacing_in, sun_needs = :sun_needs, water_needs = :water_needs WHERE id = :id"
                ),
                {"id": plant_id, "name": name, "species": species or None, "plant_family": plant_family or None, **fields},
            )

    def delete_plant(self, plant_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM plants WHERE id = :id"), {"id": plant_id})

    def list_seed_varieties(self):
        "Effective agronomic values (variety override, falling back to the plant's default) via COALESCE."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    "SELECT sv.id, sv.plant_id, sv.name, pl.name AS plant_name, "
                    "COALESCE(sv.germination_days_min, pl.germination_days_min) AS germination_days_min, "
                    "COALESCE(sv.germination_days_max, pl.germination_days_max) AS germination_days_max, "
                    "COALESCE(sv.days_to_maturity_min, pl.days_to_maturity_min) AS days_to_maturity_min, "
                    "COALESCE(sv.days_to_maturity_max, pl.days_to_maturity_max) AS days_to_maturity_max, "
                    "COALESCE(sv.spacing_in, pl.spacing_in) AS spacing_in, "
                    "COALESCE(sv.sun_needs, pl.sun_needs) AS sun_needs, "
                    "COALESCE(sv.water_needs, pl.water_needs) AS water_needs, "
                    "sv.created_at "
                    "FROM seed_varieties sv LEFT JOIN plants pl ON pl.id = sv.plant_id "
                    "ORDER BY sv.name"
                )
            ).mappings().all()

    def get_seed_variety(self, variety_id: int):
        "Raw (unjoined) columns, i.e. only this variety's own overrides -- used to prefill the edit form."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_SEED_VARIETY_COLUMNS} FROM seed_varieties WHERE id = :id"),
                {"id": variety_id},
            ).mappings().first()

    def add_seed_variety(
        self,
        plant_id: int,
        name: str,
        germination_days_min: int = None,
        germination_days_max: int = None,
        days_to_maturity_min: int = None,
        days_to_maturity_max: int = None,
        spacing_in: int = None,
        sun_needs: str = None,
        water_needs: str = None,
    ):
        fields = _agronomic_fields(
            germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max,
            spacing_in, sun_needs, water_needs,
        )
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "INSERT INTO seed_varieties (plant_id, name, germination_days_min, germination_days_max, "
                    "days_to_maturity_min, days_to_maturity_max, spacing_in, sun_needs, water_needs) "
                    "VALUES (:plant_id, :name, :germination_days_min, :germination_days_max, "
                    ":days_to_maturity_min, :days_to_maturity_max, :spacing_in, :sun_needs, :water_needs)"
                ),
                {"plant_id": plant_id, "name": name, **fields},
            )

    def update_seed_variety(
        self,
        variety_id: int,
        plant_id: int,
        name: str,
        germination_days_min: int = None,
        germination_days_max: int = None,
        days_to_maturity_min: int = None,
        days_to_maturity_max: int = None,
        spacing_in: int = None,
        sun_needs: str = None,
        water_needs: str = None,
    ):
        fields = _agronomic_fields(
            germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max,
            spacing_in, sun_needs, water_needs,
        )
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "UPDATE seed_varieties SET plant_id = :plant_id, name = :name, "
                    "germination_days_min = :germination_days_min, germination_days_max = :germination_days_max, "
                    "days_to_maturity_min = :days_to_maturity_min, days_to_maturity_max = :days_to_maturity_max, "
                    "spacing_in = :spacing_in, sun_needs = :sun_needs, water_needs = :water_needs WHERE id = :id"
                ),
                {"id": variety_id, "plant_id": plant_id, "name": name, **fields},
            )

    def delete_seed_variety(self, variety_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM seed_varieties WHERE id = :id"), {"id": variety_id})

    def list_plantings(self):
        "Joined with seed_varieties/plants so callers get effective (COALESCE'd) maturity data for expected-window math."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    "SELECT p.id, p.variety_id, p.bed_id, p.location, p.planted_date, p.quantity, "
                    "p.quantity_germinated, p.notes, p.created_at, "
                    "sv.name AS variety_name, pl.name AS plant_name, "
                    "COALESCE(sv.germination_days_min, pl.germination_days_min) AS germination_days_min, "
                    "COALESCE(sv.germination_days_max, pl.germination_days_max) AS germination_days_max, "
                    "COALESCE(sv.days_to_maturity_min, pl.days_to_maturity_min) AS days_to_maturity_min, "
                    "COALESCE(sv.days_to_maturity_max, pl.days_to_maturity_max) AS days_to_maturity_max "
                    "FROM plantings p "
                    "LEFT JOIN seed_varieties sv ON sv.id = p.variety_id "
                    "LEFT JOIN plants pl ON pl.id = sv.plant_id "
                    "ORDER BY p.planted_date DESC, p.id DESC"
                )
            ).mappings().all()

    def get_planting(self, planting_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_PLANTING_COLUMNS} FROM plantings WHERE id = :id"),
                {"id": planting_id},
            ).mappings().first()

    @staticmethod
    def _normalize_planting_fields(bed_id, location, quantity, quantity_germinated, notes):
        return {
            "bed_id": bed_id,
            "location": location or None,
            "quantity": quantity,
            "quantity_germinated": quantity_germinated,
            "notes": notes or None,
        }

    def add_planting(
        self,
        variety_id: int,
        planted_date: str,
        bed_id: int = None,
        location: str = None,
        quantity: int = None,
        quantity_germinated: int = None,
        notes: str = None,
    ):
        fields = self._normalize_planting_fields(bed_id, location, quantity, quantity_germinated, notes)
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "INSERT INTO plantings (variety_id, bed_id, location, planted_date, quantity, "
                    "quantity_germinated, notes) "
                    "VALUES (:variety_id, :bed_id, :location, :planted_date, :quantity, "
                    ":quantity_germinated, :notes)"
                ),
                {"variety_id": variety_id, "planted_date": planted_date, **fields},
            )

    def update_planting(
        self,
        planting_id: int,
        variety_id: int,
        planted_date: str,
        bed_id: int = None,
        location: str = None,
        quantity: int = None,
        quantity_germinated: int = None,
        notes: str = None,
    ):
        fields = self._normalize_planting_fields(bed_id, location, quantity, quantity_germinated, notes)
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "UPDATE plantings SET variety_id = :variety_id, planted_date = :planted_date, "
                    "bed_id = :bed_id, location = :location, quantity = :quantity, "
                    "quantity_germinated = :quantity_germinated, notes = :notes WHERE id = :id"
                ),
                {"id": planting_id, "variety_id": variety_id, "planted_date": planted_date, **fields},
            )

    def delete_planting(self, planting_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM plantings WHERE id = :id"), {"id": planting_id})


_instance = Database()


def __getattr__(name):
    """PEP 562 module delegation: db.list_notes(), db.engine, db.DB_PATH, etc. resolve against whichever 
    Database instance is current, so tests can swap it (db._instance = db.Database('.env.test')) with no 
    changes needed in main.py/pages/*.py, which always go through `db.<name>` rather than binding it early.
    """
    return getattr(_instance, name)

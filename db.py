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
    CREATE TABLE IF NOT EXISTS seed_varieties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        common_name TEXT NOT NULL,
        name TEXT NOT NULL,
        plant_family TEXT NOT NULL,
        genus TEXT,
        species TEXT,
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
    """
    CREATE TABLE IF NOT EXISTS land_plots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        width_ft INTEGER NOT NULL,
        height_ft INTEGER NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS beds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plot_id INTEGER NOT NULL,
        label TEXT NOT NULL,
        x INTEGER,
        y INTEGER,
        width_ft INTEGER NOT NULL,
        height_ft INTEGER NOT NULL,
        rotation_deg INTEGER NOT NULL DEFAULT 0,
        sun_exposure TEXT,
        irrigation_zone TEXT,
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

_SEED_VARIETY_COLUMNS = f"id, common_name, name, plant_family, genus, species, {_AGRONOMIC_COLUMNS}, created_at"

_PLANTING_COLUMNS = (
    "id, variety_id, bed_id, location, planted_date, quantity, quantity_germinated, notes, created_at"
)

_LAND_PLOT_COLUMNS = "id, name, width_ft, height_ft, created_at"

_BED_COLUMNS = (
    "id, plot_id, label, x, y, width_ft, height_ft, rotation_deg, sun_exposure, irrigation_zone, created_at"
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
    "Builds the dict of the 5 numeric + 2 text agronomic columns shared by every seed_varieties row."
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

    def list_seed_varieties(self):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_SEED_VARIETY_COLUMNS} FROM seed_varieties ORDER BY common_name, name")
            ).mappings().all()

    def get_seed_variety(self, variety_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_SEED_VARIETY_COLUMNS} FROM seed_varieties WHERE id = :id"),
                {"id": variety_id},
            ).mappings().first()

    def add_seed_variety(
        self,
        common_name: str,
        name: str,
        plant_family: str,
        genus: str = None,
        species: str = None,
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
                    "INSERT INTO seed_varieties (common_name, name, plant_family, genus, species, "
                    "germination_days_min, germination_days_max, days_to_maturity_min, days_to_maturity_max, "
                    "spacing_in, sun_needs, water_needs) "
                    "VALUES (:common_name, :name, :plant_family, :genus, :species, "
                    ":germination_days_min, :germination_days_max, :days_to_maturity_min, :days_to_maturity_max, "
                    ":spacing_in, :sun_needs, :water_needs)"
                ),
                {
                    "common_name": common_name, "name": name, "plant_family": plant_family,
                    "genus": genus or None, "species": species or None, **fields,
                },
            )

    def update_seed_variety(
        self,
        variety_id: int,
        common_name: str,
        name: str,
        plant_family: str,
        genus: str = None,
        species: str = None,
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
                    "UPDATE seed_varieties SET common_name = :common_name, name = :name, "
                    "plant_family = :plant_family, genus = :genus, species = :species, "
                    "germination_days_min = :germination_days_min, germination_days_max = :germination_days_max, "
                    "days_to_maturity_min = :days_to_maturity_min, days_to_maturity_max = :days_to_maturity_max, "
                    "spacing_in = :spacing_in, sun_needs = :sun_needs, water_needs = :water_needs WHERE id = :id"
                ),
                {
                    "id": variety_id, "common_name": common_name, "name": name, "plant_family": plant_family,
                    "genus": genus or None, "species": species or None, **fields,
                },
            )

    def delete_seed_variety(self, variety_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM seed_varieties WHERE id = :id"), {"id": variety_id})

    def list_plantings(self):
        "Joined with seed_varieties so callers get the variety's common name and maturity data for expected-window math."
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    "SELECT p.id, p.variety_id, p.bed_id, p.location, p.planted_date, p.quantity, "
                    "p.quantity_germinated, p.notes, p.created_at, "
                    "sv.name AS variety_name, sv.common_name, "
                    "sv.germination_days_min, sv.germination_days_max, "
                    "sv.days_to_maturity_min, sv.days_to_maturity_max "
                    "FROM plantings p "
                    "LEFT JOIN seed_varieties sv ON sv.id = p.variety_id "
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

    def list_land_plots(self):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_LAND_PLOT_COLUMNS} FROM land_plots ORDER BY name")
            ).mappings().all()

    def get_land_plot(self, plot_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_LAND_PLOT_COLUMNS} FROM land_plots WHERE id = :id"),
                {"id": plot_id},
            ).mappings().first()

    def add_land_plot(self, name: str, width_ft: int, height_ft: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text("INSERT INTO land_plots (name, width_ft, height_ft) VALUES (:name, :width_ft, :height_ft)"),
                {"name": name, "width_ft": width_ft, "height_ft": height_ft},
            )

    def update_land_plot(self, plot_id: int, name: str, width_ft: int, height_ft: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "UPDATE land_plots SET name = :name, width_ft = :width_ft, height_ft = :height_ft "
                    "WHERE id = :id"
                ),
                {"id": plot_id, "name": name, "width_ft": width_ft, "height_ft": height_ft},
            )

    def delete_land_plot(self, plot_id: int):
        "Deletes the plot's beds first -- there's no FK ON DELETE CASCADE, so this app-level order avoids orphans."
        for bed in self.list_beds_for_plot(plot_id):
            self.delete_bed(bed["id"])
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM land_plots WHERE id = :id"), {"id": plot_id})

    def list_beds_for_plot(self, plot_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_BED_COLUMNS} FROM beds WHERE plot_id = :plot_id ORDER BY label"),
                {"plot_id": plot_id},
            ).mappings().all()

    def get_bed(self, bed_id: int):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(f"SELECT {_BED_COLUMNS} FROM beds WHERE id = :id"), {"id": bed_id}
            ).mappings().first()

    def add_bed(
        self,
        plot_id: int,
        label: str,
        width_ft: int,
        height_ft: int,
        sun_exposure: str = None,
        irrigation_zone: str = None,
    ):
        "New beds start unplaced (x/y NULL) until dragged or 'added to map'."
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "INSERT INTO beds (plot_id, label, width_ft, height_ft, sun_exposure, irrigation_zone) "
                    "VALUES (:plot_id, :label, :width_ft, :height_ft, :sun_exposure, :irrigation_zone)"
                ),
                {
                    "plot_id": plot_id, "label": label, "width_ft": width_ft, "height_ft": height_ft,
                    "sun_exposure": sun_exposure or None, "irrigation_zone": irrigation_zone or None,
                },
            )

    def update_bed(
        self,
        bed_id: int,
        label: str,
        width_ft: int,
        height_ft: int,
        rotation_deg: int,
        sun_exposure: str = None,
        irrigation_zone: str = None,
    ):
        "Full edit of a bed's metadata/size/rotation -- does not touch position, see update_bed_position."
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "UPDATE beds SET label = :label, width_ft = :width_ft, height_ft = :height_ft, "
                    "rotation_deg = :rotation_deg, sun_exposure = :sun_exposure, irrigation_zone = :irrigation_zone "
                    "WHERE id = :id"
                ),
                {
                    "id": bed_id, "label": label, "width_ft": width_ft, "height_ft": height_ft,
                    "rotation_deg": rotation_deg, "sun_exposure": sun_exposure or None,
                    "irrigation_zone": irrigation_zone or None,
                },
            )

    def update_bed_position(self, bed_id: int, x: int, y: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text("UPDATE beds SET x = :x, y = :y WHERE id = :id"), {"id": bed_id, "x": x, "y": y}
            )

    def update_bed_size(self, bed_id: int, width_ft: int, height_ft: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text("UPDATE beds SET width_ft = :width_ft, height_ft = :height_ft WHERE id = :id"),
                {"id": bed_id, "width_ft": width_ft, "height_ft": height_ft},
            )

    def delete_bed(self, bed_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM beds WHERE id = :id"), {"id": bed_id})


_instance = Database()


def __getattr__(name):
    """PEP 562 module delegation: db.list_notes(), db.engine, db.DB_PATH, etc. resolve against whichever 
    Database instance is current, so tests can swap it (db._instance = db.Database('.env.test')) with no 
    changes needed in main.py/pages/*.py, which always go through `db.<name>` rather than binding it early.
    """
    return getattr(_instance, name)

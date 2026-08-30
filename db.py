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
]

_EVENT_COLUMNS = (
    "id, owner_id, title, start_date, end_date, start_time, end_time, notes, is_critical, created_at"
)


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

    def list_events_for_owner(self, owner_id: str):
        with self.engine.connect() as db_connection:
            return db_connection.execute(
                text(
                    f"SELECT {_EVENT_COLUMNS} FROM calendar_events "
                    "WHERE owner_id = :owner_id ORDER BY start_date, start_time"
                ),
                {"owner_id": owner_id},
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

    def add_event(self, owner_id, title, start_date, end_date, start_time, end_time, notes, is_critical):
        with self.engine.begin() as db_connection:
            db_connection.execute(
                text(
                    "INSERT INTO calendar_events "
                    "(owner_id, title, start_date, end_date, start_time, end_time, notes, is_critical) "
                    "VALUES (:owner_id, :title, :start_date, :end_date, :start_time, :end_time, :notes, :is_critical)"
                ),
                {
                    "owner_id": owner_id,
                    "title": title,
                    "start_date": start_date,
                    "end_date": end_date or start_date,
                    "start_time": start_time or None,
                    "end_time": end_time or None,
                    "notes": notes or None,
                    "is_critical": int(bool(is_critical)),
                },
            )

    def delete_event(self, event_id: int):
        with self.engine.begin() as db_connection:
            db_connection.execute(text("DELETE FROM calendar_events WHERE id = :id"), {"id": event_id})


_instance = Database()


def __getattr__(name):
    "PEP 562 module delegation: db.list_notes(), db.engine, db.DB_PATH, etc. resolve against whichever \
Database instance is current, so tests can swap it (db._instance = db.Database('.env.test')) with no \
changes needed in main.py/pages/*.py, which always go through `db.<name>` rather than binding it early."
    return getattr(_instance, name)

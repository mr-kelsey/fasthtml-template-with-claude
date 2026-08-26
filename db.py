from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import create_engine, text

env = dotenv_values(".env")

DB_PATH = env.get("DB_PATH", "data/app.db")
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db():
    with engine.begin() as conn:
        conn.execute(text(SCHEMA_SQL))


def list_notes():
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT id, title, body, created_at FROM notes ORDER BY created_at DESC, id DESC")
        ).mappings().all()


def add_note(title: str, body: str):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO notes (title, body) VALUES (:title, :body)"),
            {"title": title, "body": body},
        )


def delete_note(note_id: int):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM notes WHERE id = :id"), {"id": note_id})

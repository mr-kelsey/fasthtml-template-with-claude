# FastHTML + SQLite Template

A multipage [FastHTML](https://fastht.ml) starter with persistent storage via SQLite, using SQLAlchemy Core (`text()` queries, no ORM). Docker-ready so it can be deployed to any container-friendly host.

## Project structure

```
fasthtml-template/
├── main.py              # app entry point: wires page routers together, runs schema init on startup
├── db.py                 # SQLAlchemy engine + queries (list/add/delete notes)
├── layout.py              # shared nav/header/footer wrapper used by every page
├── static/styles.css      # small overrides on top of the default Pico CSS
├── pages/
│   ├── home.py             # GET /
│   ├── about.py            # GET /about
│   └── notes.py             # GET/POST /notes, POST /notes/{id}/delete — SQLite CRUD demo
├── Dockerfile              # containerizes the app (uvicorn, not the dev-only serve())
├── docker-compose.yml       # the app, with the SQLite file persisted in a named volume
├── tests/                     # pytest suite (db.py unit tests + route integration tests)
├── .env.example              # copy to .env and fill in
├── requirements.txt
└── requirements-dev.txt       # requirements.txt + pytest
```

## Run with Docker Compose (recommended)

```bash
cp .env.example .env
docker compose up --build
```

Visit `http://localhost:5001`. Notes persist in the `sqlite_data` volume across restarts (`docker compose restart app` and your data is still there).

## Run without Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit DB_PATH if you want the SQLite file somewhere other than data/app.db
python main.py
```

`main.py` calls `serve()` when run directly, which starts a dev server with autoreload.

## Environment variables

| Variable | Used by | Notes |
| --- | --- | --- |
| `PORT` | app | port the app listens on (default `5001`) |
| `DB_PATH` | app | path to the SQLite database file (default `data/app.db`); the parent directory is created automatically |

## Running tests

No external services needed — tests run against a local SQLite file:

```bash
cp .env.example .env   # if you haven't already
pip install -r requirements-dev.txt
pytest
```

The suite (`tests/`) covers `db.py`'s queries directly and the page routes end-to-end via Starlette's `TestClient`. It connects using the same `.env` config as the app, and truncates the `notes` table before and after every test — don't point it at a database whose notes you want to keep. For full isolation, set `DB_PATH` to a separate file before running `pytest`.

## Adding a new page

1. Create `pages/foo.py`:
   ```python
   from fasthtml import common as fast
   from layout import layout

   router = APIRouter()

   @router("/foo", methods=["get"])
   def foo_page():
       return layout("Foo", fast.H1("Foo"))
   ```
2. Import it and add it to the loop in `main.py`:
   ```python
   from pages import home, about, notes, foo
   ...
   for page_module in (home, about, notes, foo):
       page_module.router.to_app(app)
   ```
3. Optionally add a link in `layout.py`'s `NAV_LINKS`.

## Notes demo

`pages/notes.py` + `db.py` show the full pattern: a `notes` table (`id`, `title`, `body`, `created_at`), created idempotently on startup via `CREATE TABLE IF NOT EXISTS`, queried with SQLAlchemy Core's `text()` and bound `:params` (no string-interpolated SQL), and rendered through FT tags (auto-escaped, no raw HTML interpolation).

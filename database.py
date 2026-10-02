import sqlite3
import os
from flask import current_app, g


def get_db():
    """Return a SQLite connection stored on the request/application context."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Create the instance folder and (re)build the schema."""
    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
    with app.app_context():
        db = get_db()
        with open(app.config["SCHEMA_PATH"], "r") as f:
            db.executescript(f.read())
        db.commit()


def db_exists(app):
    return os.path.exists(app.config["DATABASE"])


def register_db(app):
    app.teardown_appcontext(close_db)

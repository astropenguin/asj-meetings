__all__ = ["connect", "where"]


# standard library
import sqlite3 as sqlite
from pathlib import Path


# dependencies
from platformdirs import user_data_dir


# constants
DB = Path(user_data_dir("asj-meetings")) / "main.db"


def connect() -> sqlite.Connection:
    """Connect to the SQLite database."""
    if not DB.parent.exists():
        DB.parent.mkdir(parents=True, exist_ok=True)

    return sqlite.connect(DB)


def where() -> Path:
    """Get the path to the SQLite database."""
    return DB

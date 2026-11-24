"""SQLite storage for studysprint.

The database is a single local file (default
``~/.local/share/studysprint/studysprint.db``, overridable with the
``STUDYSPRINT_DB`` environment variable). No network, no accounts.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from .models import Course, Session

SCHEMA = """
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    cus INTEGER NOT NULL CHECK (cus > 0),
    target_hours REAL NOT NULL CHECK (target_hours > 0),
    deadline TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'done'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL REFERENCES courses(id),
    minutes INTEGER NOT NULL CHECK (minutes > 0),
    session_date TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT ''
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open (and create, if needed) the database at ``db_path``."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _course_from_row(row: sqlite3.Row) -> Course:
    return Course(
        id=row["id"],
        name=row["name"],
        cus=row["cus"],
        target_hours=row["target_hours"],
        deadline=date.fromisoformat(row["deadline"]),
        status=row["status"],
    )


def add_course(
    conn: sqlite3.Connection,
    name: str,
    cus: int,
    target_hours: float,
    deadline: date,
) -> Course:
    """Insert a course. Raises ValueError if the name already exists."""
    try:
        cur = conn.execute(
            "INSERT INTO courses (name, cus, target_hours, deadline)"
            " VALUES (?, ?, ?, ?)",
            (name, cus, target_hours, deadline.isoformat()),
        )
    except sqlite3.IntegrityError as exc:
        raise ValueError(f"a course named {name!r} already exists") from exc
    conn.commit()
    return get_course(conn, cur.lastrowid)


def get_course(conn: sqlite3.Connection, course_id: int) -> Course:
    row = conn.execute(
        "SELECT * FROM courses WHERE id = ?", (course_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"no course with id {course_id}")
    return _course_from_row(row)


def get_course_by_name(conn: sqlite3.Connection, name: str) -> Course:
    row = conn.execute(
        "SELECT * FROM courses WHERE name = ?", (name,)
    ).fetchone()
    if row is None:
        raise ValueError(f"no course named {name!r}")
    return _course_from_row(row)


def list_courses(
    conn: sqlite3.Connection, status: str | None = None
) -> list[Course]:
    query = "SELECT * FROM courses"
    params: tuple = ()
    if status is not None:
        query += " WHERE status = ?"
        params = (status,)
    query += " ORDER BY deadline, name"
    return [_course_from_row(r) for r in conn.execute(query, params)]


def complete_course(conn: sqlite3.Connection, course_id: int) -> Course:
    conn.execute(
        "UPDATE courses SET status = 'done' WHERE id = ?", (course_id,)
    )
    conn.commit()
    return get_course(conn, course_id)


def log_session(
    conn: sqlite3.Connection,
    course_id: int,
    minutes: int,
    session_date: date,
    note: str = "",
) -> Session:
    course = get_course(conn, course_id)
    cur = conn.execute(
        "INSERT INTO sessions (course_id, minutes, session_date, note)"
        " VALUES (?, ?, ?, ?)",
        (course_id, minutes, session_date.isoformat(), note),
    )
    conn.commit()
    return Session(
        id=cur.lastrowid,
        course_id=course_id,
        course_name=course.name,
        minutes=minutes,
        session_date=session_date,
        note=note,
    )


def list_sessions(
    conn: sqlite3.Connection, course_id: int | None = None
) -> list[Session]:
    query = (
        "SELECT s.*, c.name AS course_name FROM sessions s"
        " JOIN courses c ON c.id = s.course_id"
    )
    params: tuple = ()
    if course_id is not None:
        query += " WHERE s.course_id = ?"
        params = (course_id,)
    query += " ORDER BY s.session_date DESC, s.id DESC"
    rows = conn.execute(query, params).fetchall()
    return [
        Session(
            id=r["id"],
            course_id=r["course_id"],
            course_name=r["course_name"],
            minutes=r["minutes"],
            session_date=date.fromisoformat(r["session_date"]),
            note=r["note"],
        )
        for r in rows
    ]


def minutes_logged(conn: sqlite3.Connection, course_id: int) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(minutes), 0) AS total FROM sessions"
        " WHERE course_id = ?",
        (course_id,),
    ).fetchone()
    return int(row["total"])


def minutes_logged_since(
    conn: sqlite3.Connection, course_id: int, since: date
) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(minutes), 0) AS total FROM sessions"
        " WHERE course_id = ? AND session_date >= ?",
        (course_id, since.isoformat()),
    ).fetchone()
    return int(row["total"])


def session_dates(conn: sqlite3.Connection) -> list[date]:
    rows = conn.execute(
        "SELECT DISTINCT session_date FROM sessions ORDER BY session_date"
    ).fetchall()
    return [date.fromisoformat(r["session_date"]) for r in rows]


def total_minutes_between(
    conn: sqlite3.Connection, start: date, end: date
) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(minutes), 0) AS total FROM sessions"
        " WHERE session_date >= ? AND session_date <= ?",
        (start.isoformat(), end.isoformat()),
    ).fetchone()
    return int(row["total"])

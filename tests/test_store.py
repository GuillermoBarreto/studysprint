"""Tests for studysprint.store (SQLite storage)."""

from datetime import date

import pytest

from studysprint import store


@pytest.fixture
def conn(tmp_path):
    connection = store.connect(tmp_path / "test.db")
    yield connection
    connection.close()


def test_add_and_list_courses(conn):
    course = store.add_course(conn, "D335", 3, 40.0, date(2026, 12, 11))
    assert course.name == "D335"
    assert course.cus == 3
    assert course.target_minutes == 2400
    assert course.status == "active"
    courses = store.list_courses(conn)
    assert [c.name for c in courses] == ["D335"]


def test_courses_listed_by_deadline(conn):
    store.add_course(conn, "LATER", 3, 20.0, date(2027, 1, 15))
    store.add_course(conn, "SOON", 4, 30.0, date(2026, 12, 1))
    assert [c.name for c in store.list_courses(conn)] == ["SOON", "LATER"]


def test_duplicate_course_name_rejected(conn):
    store.add_course(conn, "D335", 3, 40.0, date(2026, 12, 11))
    with pytest.raises(ValueError, match="already exists"):
        store.add_course(conn, "D335", 3, 40.0, date(2026, 12, 11))


def test_log_session_and_minutes_logged(conn):
    course = store.add_course(conn, "D335", 3, 40.0, date(2026, 12, 11))
    store.log_session(conn, course.id, 45, date(2026, 11, 23), "chapter 1")
    store.log_session(conn, course.id, 30, date(2026, 11, 24))
    assert store.minutes_logged(conn, course.id) == 75
    sessions = store.list_sessions(conn, course.id)
    assert len(sessions) == 2
    assert sessions[0].minutes == 30  # newest first
    assert sessions[1].note == "chapter 1"


def test_minutes_logged_since(conn):
    course = store.add_course(conn, "D335", 3, 40.0, date(2026, 12, 11))
    store.log_session(conn, course.id, 45, date(2026, 11, 10))
    store.log_session(conn, course.id, 30, date(2026, 11, 23))
    assert store.minutes_logged_since(conn, course.id, date(2026, 11, 20)) == 30


def test_complete_course(conn):
    course = store.add_course(conn, "D335", 3, 40.0, date(2026, 12, 11))
    done = store.complete_course(conn, course.id)
    assert done.status == "done"
    assert store.list_courses(conn, status="active") == []
    assert [c.name for c in store.list_courses(conn, status="done")] == ["D335"]


def test_unknown_course_errors(conn):
    with pytest.raises(ValueError, match="no course named"):
        store.get_course_by_name(conn, "NOPE")
    with pytest.raises(ValueError, match="no course with id"):
        store.get_course(conn, 99)


def test_session_dates_and_weekly_total(conn):
    course = store.add_course(conn, "D335", 3, 40.0, date(2026, 12, 11))
    store.log_session(conn, course.id, 45, date(2026, 11, 22))
    store.log_session(conn, course.id, 30, date(2026, 11, 23))
    assert store.session_dates(conn) == [date(2026, 11, 22), date(2026, 11, 23)]
    assert store.total_minutes_between(
        conn, date(2026, 11, 22), date(2026, 11, 23)
    ) == 75
    assert store.total_minutes_between(
        conn, date(2026, 11, 1), date(2026, 11, 2)
    ) == 0

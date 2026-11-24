"""Command-line interface for studysprint.

Usage examples::

    studysprint add-course D335 --cus 3 --hours 40 --deadline 2026-12-11
    studysprint log D335 --minutes 45
    studysprint plan
    studysprint status
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

from . import planner, store
from .models import Course

DEFAULT_DB = Path.home() / ".local" / "share" / "studysprint" / "studysprint.db"


def default_db_path() -> Path:
    override = os.environ.get("STUDYSPRINT_DB")
    return Path(override) if override else DEFAULT_DB


def parse_date(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid date {text!r}; use YYYY-MM-DD"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="studysprint",
        description="Plan study time for self-paced degree courses.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="path to the SQLite database (default: %(default)s)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add-course", help="add a course to the plan")
    add.add_argument("name", help="course code or short name, e.g. D335")
    add.add_argument("--cus", type=int, required=True,
                     help="competency units the course is worth")
    add.add_argument("--hours", type=float, required=True,
                     help="estimated hours needed to finish the course")
    add.add_argument("--deadline", type=parse_date, required=True,
                     help="deadline as YYYY-MM-DD")

    sub.add_parser("courses", help="list courses ordered by deadline")

    log = sub.add_parser("log", help="log a study session")
    log.add_argument("course", help="course name")
    log.add_argument("--minutes", type=int, required=True,
                     help="minutes studied")
    log.add_argument("--date", type=parse_date, default=date.today(),
                     help="session date as YYYY-MM-DD (default: today)")
    log.add_argument("--note", default="", help="short note about the session")

    sessions = sub.add_parser("sessions", help="list logged sessions")
    sessions.add_argument("course", nargs="?",
                          help="only sessions for this course")

    plan = sub.add_parser("plan", help="show the daily minutes each course needs")
    plan.add_argument("--date", type=parse_date, default=date.today(),
                      help="plan as of YYYY-MM-DD (default: today)")

    status = sub.add_parser("status", help="show progress and projected finish dates")
    status.add_argument("--date", type=parse_date, default=date.today(),
                        help="status as of YYYY-MM-DD (default: today)")

    complete = sub.add_parser("complete", help="mark a course done")
    complete.add_argument("course", help="course name")

    sub.add_parser("summary", help="show the last 7 days and the current streak")
    return parser


def _open_db(args: argparse.Namespace) -> sqlite3.Connection:
    return store.connect(args.db or default_db_path())


def _course_or_exit(conn: sqlite3.Connection, name: str) -> Course:
    try:
        return store.get_course_by_name(conn, name)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def cmd_add_course(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    if args.cus <= 0 or args.hours <= 0:
        print("error: --cus and --hours must be positive", file=sys.stderr)
        return 2
    try:
        course = store.add_course(
            conn, args.name, args.cus, args.hours, args.deadline
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        f"Added {course.name} ({course.cus} CUs, "
        f"{course.target_hours:g}h target, due {course.deadline})."
    )
    return 0


def cmd_courses(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    courses = store.list_courses(conn)
    if not courses:
        print("No courses yet. Add one with: studysprint add-course NAME "
              "--cus 3 --hours 40 --deadline 2026-12-11")
        return 0
    print(f"{'Course':<12}{'CUs':>4}  {'Target':>7}  {'Deadline':<11}  Status")
    for course in courses:
        print(
            f"{course.name:<12}{course.cus:>4}  "
            f"{course.target_hours:>6g}h  {course.deadline:<11}  {course.status}"
        )
    return 0


def cmd_log(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    if args.minutes <= 0:
        print("error: --minutes must be positive", file=sys.stderr)
        return 2
    course = _course_or_exit(conn, args.course)
    session = store.log_session(
        conn, course.id, args.minutes, args.date, args.note
    )
    total = store.minutes_logged(conn, course.id)
    print(
        f"Logged {session.minutes} min for {course.name} on {session.session_date}"
        f" ({total} min total, {course.target_minutes - total} min to go)."
        if total < course.target_minutes
        else f"Logged {session.minutes} min for {course.name} on "
        f"{session.session_date} — target reached ({total} min total)."
    )
    return 0


def cmd_sessions(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    course_id = None
    if args.course:
        course_id = _course_or_exit(conn, args.course).id
    sessions = store.list_sessions(conn, course_id)
    if not sessions:
        print("No sessions logged yet.")
        return 0
    for session in sessions:
        note = f" — {session.note}" if session.note else ""
        print(
            f"{session.session_date}  {session.course_name:<12}"
            f"{session.minutes:>4} min{note}"
        )
    return 0


def _plans(conn: sqlite3.Connection, today: date) -> list[planner.CoursePlan]:
    plans = []
    window_start = today - timedelta(days=planner.PACE_WINDOW_DAYS - 1)
    for course in store.list_courses(conn, status="active"):
        logged = store.minutes_logged(conn, course.id)
        recent = store.minutes_logged_since(conn, course.id, window_start)
        pace = planner.average_daily_pace(recent)
        plans.append(planner.plan_course(course, logged, pace, today))
    return plans


def cmd_plan(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    plans = _plans(conn, args.date)
    if not plans:
        print("No active courses. Add one with: studysprint add-course ...")
        return 0
    total = 0
    print(f"Daily plan for {args.date} (minutes per day to finish on time):")
    for plan in plans:
        total += plan.minutes_per_day
        if plan.done:
            line = f"  {plan.course.name:<12} done — target reached"
        elif plan.overdue:
            line = (
                f"  {plan.course.name:<12} OVERDUE by {-plan.days_left}d — "
                f"{plan.minutes_remaining} min left, do it today"
            )
        else:
            line = (
                f"  {plan.course.name:<12} {plan.minutes_per_day:>4} min/day"
                f"  ({plan.minutes_remaining} min left, {plan.days_left}d to go)"
            )
        print(line)
    print(f"Total: {total} min/day across {len(plans)} active course(s).")
    return 0


def cmd_status(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    plans = _plans(conn, args.date)
    if not plans:
        print("No active courses. Add one with: studysprint add-course ...")
        return 0
    for plan in plans:
        course = plan.course
        fraction = (
            plan.minutes_logged / course.target_minutes
            if course.target_minutes
            else 0.0
        )
        bar = planner.progress_bar(fraction)
        finish = (
            f"projected finish {plan.projected_finish}"
            if plan.projected_finish and not plan.done
            else ("finished" if plan.done else "no pace yet — log a session")
        )
        due = (
            f"due {course.deadline} ({plan.days_left}d left)"
            if plan.days_left >= 0
            else f"due {course.deadline} (OVERDUE by {-plan.days_left}d)"
        )
        print(f"{course.name} ({course.cus} CUs) — {due}")
        print(
            f"  {bar} {plan.minutes_logged}/{course.target_minutes} min"
            f"  · {finish}"
        )
    return 0


def cmd_complete(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    course = _course_or_exit(conn, args.course)
    store.complete_course(conn, course.id)
    print(f"{course.name} marked done.")
    return 0


def cmd_summary(conn: sqlite3.Connection, args: argparse.Namespace) -> int:
    today = date.today()
    week_start = today - timedelta(days=6)
    total = store.total_minutes_between(conn, week_start, today)
    streak = planner.current_streak(store.session_dates(conn), today)
    print(f"Last 7 days ({week_start} to {today}): {total} min studied.")
    print(f"Current streak: {streak} day(s).")
    return 0


COMMANDS = {
    "add-course": cmd_add_course,
    "courses": cmd_courses,
    "log": cmd_log,
    "sessions": cmd_sessions,
    "plan": cmd_plan,
    "status": cmd_status,
    "complete": cmd_complete,
    "summary": cmd_summary,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    conn = _open_db(args)
    try:
        return COMMANDS[args.command](conn, args)
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

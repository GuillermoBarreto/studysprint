"""Pure planning math for studysprint.

Every function here is a pure function of explicit inputs, so the
planning rules are unit-testable without touching the database.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

from .models import Course

PACE_WINDOW_DAYS = 14


@dataclass
class CoursePlan:
    course: Course
    minutes_logged: int
    minutes_remaining: int
    days_left: int
    minutes_per_day: int
    overdue: bool
    done: bool
    projected_finish: date | None


def days_left(deadline: date, today: date) -> int:
    """Whole days from ``today`` until ``deadline`` (negative if past)."""
    return (deadline - today).days


def minutes_remaining(course: Course, logged_minutes: int) -> int:
    """Minutes still needed to reach the course's target workload."""
    return max(0, course.target_minutes - logged_minutes)


def minutes_per_day(course: Course, logged_minutes: int, today: date) -> int:
    """Daily minutes needed to finish on time.

    Spreads the remaining minutes evenly over the days left. A course
    due today (or already past due) needs all remaining minutes today.
    A finished course needs zero.
    """
    remaining = minutes_remaining(course, logged_minutes)
    if remaining == 0:
        return 0
    span = max(1, days_left(course.deadline, today))
    return math.ceil(remaining / span)


def average_daily_pace(
    minutes_in_window: int, window_days: int = PACE_WINDOW_DAYS
) -> float:
    """Average minutes studied per day over the trailing window."""
    if window_days <= 0:
        return 0.0
    return minutes_in_window / window_days


def projected_finish(
    course: Course, logged_minutes: int, pace_per_day: float, today: date
) -> date | None:
    """Date the course finishes if the current pace holds.

    Returns None when there is no pace to project from, or when the
    course is already finished.
    """
    remaining = minutes_remaining(course, logged_minutes)
    if remaining == 0:
        return today
    if pace_per_day <= 0:
        return None
    days_needed = math.ceil(remaining / pace_per_day)
    return today + timedelta(days=days_needed)


def plan_course(
    course: Course, logged_minutes: int, pace_per_day: float, today: date
) -> CoursePlan:
    """Full daily plan for one course."""
    remaining = minutes_remaining(course, logged_minutes)
    days = days_left(course.deadline, today)
    return CoursePlan(
        course=course,
        minutes_logged=logged_minutes,
        minutes_remaining=remaining,
        days_left=days,
        minutes_per_day=minutes_per_day(course, logged_minutes, today),
        overdue=days < 0 and remaining > 0,
        done=remaining == 0,
        projected_finish=projected_finish(
            course, logged_minutes, pace_per_day, today
        ),
    )


def progress_bar(fraction: float, width: int = 20) -> str:
    """A text progress bar, e.g. ``[██████░░░░░░░░░░░░░░] 30%``."""
    clamped = min(1.0, max(0.0, fraction))
    filled = int(round(clamped * width))
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {int(round(clamped * 100))}%"


def current_streak(study_dates: list[date], today: date) -> int:
    """Consecutive days with at least one session, ending today.

    A session yesterday still counts: the streak is alive until a full
    day passes with no study. Returns 0 when nothing was logged
    yesterday or today.
    """
    days = set(study_dates)
    if today not in days and (today - timedelta(days=1)) not in days:
        return 0
    streak = 0
    cursor = today
    if cursor not in days:
        cursor -= timedelta(days=1)
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak

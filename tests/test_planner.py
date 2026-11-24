"""Tests for the pure planning math in studysprint.planner."""

from datetime import date, timedelta

from studysprint.models import Course
from studysprint.planner import (
    current_streak,
    minutes_per_day,
    minutes_remaining,
    plan_course,
    progress_bar,
    projected_finish,
)

TODAY = date(2026, 11, 23)


def make_course(deadline, target_hours=40.0, name="D335"):
    return Course(
        id=1, name=name, cus=3, target_hours=target_hours, deadline=deadline
    )


def test_remaining_minutes_counts_down_to_zero():
    course = make_course(date(2026, 12, 11))
    assert minutes_remaining(course, 0) == 2400
    assert minutes_remaining(course, 600) == 1800
    assert minutes_remaining(course, 2400) == 0
    assert minutes_remaining(course, 3000) == 0


def test_minutes_per_day_spreads_evenly():
    # 40h = 2400 min, 18 days left (Nov 23 -> Dec 11): 2400 / 18 = 133.33
    course = make_course(date(2026, 12, 11))
    assert minutes_per_day(course, 0, TODAY) == 134
    # Half done: 1200 / 18 = 66.67
    assert minutes_per_day(course, 1200, TODAY) == 67


def test_minutes_per_day_due_today_needs_it_all():
    course = make_course(TODAY)
    assert minutes_per_day(course, 1200, TODAY) == 1200


def test_minutes_per_day_overdue_needs_it_all():
    course = make_course(date(2026, 11, 20))
    assert minutes_per_day(course, 1200, TODAY) == 1200


def test_minutes_per_day_finished_course_is_zero():
    course = make_course(date(2026, 12, 11))
    assert minutes_per_day(course, 2400, TODAY) == 0


def test_projected_finish_from_pace():
    course = make_course(date(2026, 12, 11))
    # 1200 min left at 100 min/day -> 12 days -> Dec 5
    assert projected_finish(course, 1200, 100.0, TODAY) == date(2026, 12, 5)


def test_projected_finish_none_without_pace():
    course = make_course(date(2026, 12, 11))
    assert projected_finish(course, 1200, 0.0, TODAY) is None


def test_projected_finish_finished_course_is_today():
    course = make_course(date(2026, 12, 11))
    assert projected_finish(course, 2400, 0.0, TODAY) == TODAY


def test_plan_course_flags_overdue():
    course = make_course(date(2026, 11, 20))
    plan = plan_course(course, 100, 50.0, TODAY)
    assert plan.overdue is True
    assert plan.days_left == -3
    assert plan.done is False


def test_plan_course_flags_done():
    course = make_course(date(2026, 12, 11))
    plan = plan_course(course, 2400, 50.0, TODAY)
    assert plan.done is True
    assert plan.minutes_per_day == 0


def test_progress_bar():
    assert progress_bar(0.0) == "[░░░░░░░░░░░░░░░░░░░░] 0%"
    assert progress_bar(0.5) == "[██████████░░░░░░░░░░] 50%"
    assert progress_bar(1.0) == "[████████████████████] 100%"
    assert progress_bar(1.5) == "[████████████████████] 100%"


def test_current_streak_counts_back_from_today():
    days = [TODAY - timedelta(days=i) for i in range(5)]
    assert current_streak(days, TODAY) == 5


def test_current_streak_allows_a_missing_today():
    days = [TODAY - timedelta(days=i) for i in range(1, 4)]
    assert current_streak(days, TODAY) == 3


def test_current_streak_breaks_on_a_gap():
    days = [TODAY, TODAY - timedelta(days=2), TODAY - timedelta(days=3)]
    assert current_streak(days, TODAY) == 1


def test_current_streak_zero_when_nothing_recent():
    assert current_streak([TODAY - timedelta(days=5)], TODAY) == 0
    assert current_streak([], TODAY) == 0

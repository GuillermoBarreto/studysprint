"""Data model for studysprint."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class Course:
    """One self-paced course with a deadline and an estimated workload."""

    id: int
    name: str
    cus: int
    target_hours: float
    deadline: date
    status: str = "active"  # "active" or "done"

    @property
    def target_minutes(self) -> int:
        return int(round(self.target_hours * 60))


@dataclass
class Session:
    """One logged study session."""

    id: int
    course_id: int
    course_name: str
    minutes: int
    session_date: date
    note: str = ""

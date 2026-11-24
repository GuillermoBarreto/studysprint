"""End-to-end CLI tests: run main() against a temporary database."""

import pytest

from studysprint.cli import main


@pytest.fixture
def db_env(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDYSPRINT_DB", str(tmp_path / "cli.db"))


def run(argv):
    return main(argv)


def test_full_flow_add_log_plan_status(db_env, capsys):
    assert run(["add-course", "D335", "--cus", "3", "--hours", "40",
                "--deadline", "2026-12-11"]) == 0
    out = capsys.readouterr().out
    assert "Added D335" in out

    assert run(["log", "D335", "--minutes", "45",
                "--date", "2026-11-23"]) == 0
    out = capsys.readouterr().out
    assert "Logged 45 min for D335" in out

    assert run(["plan", "--date", "2026-11-23"]) == 0
    out = capsys.readouterr().out
    # 2355 min left over 18 days -> 131 min/day
    assert "131 min/day" in out
    assert "Total: 131 min/day" in out

    assert run(["status", "--date", "2026-11-23"]) == 0
    out = capsys.readouterr().out
    assert "D335 (3 CUs)" in out
    assert "45/2400 min" in out

    assert run(["summary"]) == 0
    out = capsys.readouterr().out
    assert "min studied" in out


def test_log_unknown_course_fails(db_env, capsys):
    with pytest.raises(SystemExit) as exc:
        run(["log", "NOPE", "--minutes", "30"])
    assert exc.value.code == 2
    assert "no course named" in capsys.readouterr().err


def test_add_duplicate_course_fails(db_env, capsys):
    assert run(["add-course", "D335", "--cus", "3", "--hours", "40",
                "--deadline", "2026-12-11"]) == 0
    assert run(["add-course", "D335", "--cus", "3", "--hours", "40",
                "--deadline", "2026-12-11"]) == 2
    assert "already exists" in capsys.readouterr().err


def test_complete_course(db_env, capsys):
    run(["add-course", "D335", "--cus", "3", "--hours", "40",
         "--deadline", "2026-12-11"])
    capsys.readouterr()
    assert run(["complete", "D335"]) == 0
    assert "marked done" in capsys.readouterr().out
    assert run(["plan", "--date", "2026-11-23"]) == 0
    assert "No active courses" in capsys.readouterr().out


def test_empty_plan_message(db_env, capsys):
    assert run(["plan"]) == 0
    assert "No active courses" in capsys.readouterr().out

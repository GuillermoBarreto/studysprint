# studysprint

A CLI study planner for self-paced degree courses. Give it your courses,
their deadlines, and an estimated workload, and it tells you how many
minutes to study each day to finish on time — then tracks your sessions
and projects your finish date at your current pace.

## Why

Self-paced programs hand you a deadline and leave the daily planning to
you. studysprint turns "40 hours by December 11" into "131 minutes a day",
recalculates that number every time you log a session, and shows whether
your current pace gets you there.

## Install

Requires Python 3.11+.

```bash
pip install .
```

## Usage

Add a course with its competency units, estimated hours, and deadline:

```bash
studysprint add-course D335 --cus 3 --hours 40 --deadline 2026-12-11
```

Log study sessions as you go:

```bash
studysprint log D335 --minutes 45 --note "finished chapter 3"
studysprint log D335 --minutes 30 --date 2026-11-22
```

See what today needs:

```bash
studysprint plan
# Daily plan for 2026-11-23 (minutes per day to finish on time):
#   D335          131 min/day  (2355 min left, 18d to go)
# Total: 131 min/day across 1 active course(s).
```

Check progress and projected finish dates:

```bash
studysprint status
# D335 (3 CUs) — due 2026-12-11 (18d left)
#   [░░░░░░░░░░░░░░░░░░░░] 2% 45/2400 min  · projected finish 2027-01-15
```

Other commands:

```bash
studysprint courses          # list courses ordered by deadline
studysprint sessions D335    # list logged sessions for a course
studysprint summary          # last 7 days + current streak
studysprint complete D335    # mark a course done
```

Data lives in a local SQLite file at
`~/.local/share/studysprint/studysprint.db` (override with
`STUDYSPRINT_DB` or `--db`). No network, no accounts, no API keys.

## How the plan works

- **Minutes per day** = remaining minutes ÷ days left, rounded up.
  A course due today (or past due) needs all remaining minutes today.
- **Projected finish** uses your average minutes per day over the last
  14 days. With no sessions logged yet, there is no pace to project from.
- **Streak** counts consecutive days with at least one logged session,
  ending today (yesterday still counts if today has no session yet).

## Development

```bash
python -m pytest
```

## Roadmap

- `export` command: weekly plan as Markdown for a blog or journal
- Per-course weekly targets and a `--week` view in `plan`
- Import courses from a CSV
- Optional reminders when a course slips behind its projected finish

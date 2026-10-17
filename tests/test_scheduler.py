"""
Intelligent Department Timetable Scheduler - Automated Test Suite

Verifies:
  (a) No faculty conflicts across all classes (no faculty assigned to two classes in the same period)
  (b) Fixed lunch break (12:30 - 1:05 PM) is respected and short breaks are placed between periods
  (c) Full-time and part-time load limits and working windows are strictly respected
  (d) Subject constraints: exactly 1 period per class per day, configured weekly periods matched
  (e) Graceful error handling with descriptive messages on impossible constraints
"""

import os
import pytest
import database
from config import (
    DAYS_OF_WEEK,
    LUNCH_BREAK_START,
    LUNCH_BREAK_END,
    LUNCH_BREAK_AFTER_PERIOD,
    SHORT_BREAK_1_AFTER_PERIOD,
    SHORT_BREAK_2_AFTER_PERIOD,
    PART_TIME_ALLOWED_PERIODS,
    FULL_TIME_ALLOWED_PERIODS,
    WORK_TYPE_PART_TIME,
    WORK_TYPE_FULL_TIME,
    MAX_FULL_TIME_DAILY_PERIODS,
    PERIOD_TIMINGS,
    BREAK_TIMINGS,
)
from database import init_db, seed_sample_data_if_empty, get_db_connection
from scheduler import TimetableScheduler, SchedulingError

TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_scheduler.db")

@pytest.fixture(autouse=True)
def setup_test_db():
    """Initializes and seeds an isolated test database before each test run."""
    original_db = database.DB_PATH
    database.DB_PATH = TEST_DB_PATH
    init_db(force=True)
    seed_sample_data_if_empty()
    yield
    database.DB_PATH = original_db
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass


def test_no_faculty_double_booking():
    """
    Requirement (a): No faculty conflicts across all classes.
    Verifies that no faculty member is assigned to two different classes in the same (day, period).
    """
    scheduler = TimetableScheduler()
    res = scheduler.generate()
    assert res["success"] is True

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT faculty_id, day, period_num, COUNT(DISTINCT class_id) as class_count
        FROM timetable_entries
        GROUP BY faculty_id, day, period_num
        HAVING class_count > 1;
    """)
    conflicts = cursor.fetchall()
    conn.close()

    assert len(conflicts) == 0, f"Found {len(conflicts)} faculty double-booking conflicts: {[dict(c) for c in conflicts]}"


def test_breaks_and_period_timings_respected():
    """
    Requirement (b): Fixed lunch break is respected and short breaks are placed between periods.
    """
    # 1. Verify Named Constants for Fixed Lunch Break
    assert LUNCH_BREAK_START == "12:30", "Lunch break start must be 12:30 PM"
    assert LUNCH_BREAK_END == "13:05", "Lunch break end must be 1:05 PM"
    assert LUNCH_BREAK_AFTER_PERIOD == 4, "Lunch break must be placed after Period 4"

    # 2. Verify Automatic Short Break Placements
    assert SHORT_BREAK_1_AFTER_PERIOD == 2, "Morning break must be placed between Period 2 and 3"
    assert SHORT_BREAK_2_AFTER_PERIOD == 6, "Afternoon break must be placed between Period 6 and 7"

    # 3. Verify Period Timing Sequence
    assert PERIOD_TIMINGS[1]["start"] == "09:00"
    assert PERIOD_TIMINGS[4]["end"] == "12:30"   # Leads directly into Lunch break
    assert PERIOD_TIMINGS[5]["start"] == "13:05" # Starts immediately after Lunch break
    assert PERIOD_TIMINGS[8]["end"] == "16:45"   # End of college day

    # 4. Verify Break metadata is properly published
    assert BREAK_TIMINGS["lunch_break"]["type"] == "fixed_lunch_break"
    assert BREAK_TIMINGS["short_break_1"]["type"] == "automatic_short_break"
    assert BREAK_TIMINGS["short_break_2"]["type"] == "automatic_short_break"


def test_faculty_windows_and_load_limits():
    """
    Requirement (c): Full-time and part-time load limits and working windows are respected.
    - Part-time faculty must ONLY be scheduled in periods 1..4 (09:00 AM - 12:30 PM).
      Under no circumstances can they be scheduled in periods 5..8.
    - Part-time weekly assigned periods must not exceed individual weekly_period_limit.
    - Full-time faculty must not exceed 8 periods/day.
    """
    scheduler = TimetableScheduler()
    res = scheduler.generate()
    assert res["success"] is True

    conn = get_db_connection()
    cursor = conn.cursor()

    # Query all assigned entries joined with faculty info
    cursor.execute("""
        SELECT t.id, t.faculty_id, t.day, t.period_num,
               f.name, f.work_type, f.weekly_period_limit
        FROM timetable_entries t
        JOIN faculty f ON t.faculty_id = f.id;
    """)
    entries = [dict(r) for r in cursor.fetchall()]

    # Query individual faculty assigned totals
    cursor.execute("""
        SELECT f.id, f.name, f.work_type, f.weekly_period_limit,
               COUNT(t.id) as total_assigned
        FROM faculty f
        LEFT JOIN timetable_entries t ON f.id = t.faculty_id
        GROUP BY f.id;
    """)
    faculty_loads = [dict(r) for r in cursor.fetchall()]
    conn.close()

    # Verification 1: Part-time window enforcement (Periods 1-4 only)
    for entry in entries:
        if entry["work_type"] == WORK_TYPE_PART_TIME:
            assert entry["period_num"] in PART_TIME_ALLOWED_PERIODS, (
                f"VIOLATION: Part-time faculty '{entry['name']}' scheduled in Period {entry['period_num']}! "
                f"Part-time faculty must be restricted to periods 1-4 (09:00 - 12:30)."
            )

    # Verification 2: Weekly limits respected
    for fl in faculty_loads:
        limit = fl["weekly_period_limit"]
        assigned = fl["total_assigned"]
        assert assigned <= limit, (
            f"VIOLATION: Faculty '{fl['name']}' ({fl['work_type']}) assigned {assigned} periods, "
            f"exceeding weekly limit of {limit}!"
        )

    # Verification 3: Full-time daily limit (at most 8 periods/day)
    daily_loads = {}
    for entry in entries:
        key = (entry["faculty_id"], entry["day"])
        daily_loads[key] = daily_loads.get(key, 0) + 1

    for (fid, day), count in daily_loads.items():
        assert count <= MAX_FULL_TIME_DAILY_PERIODS, (
            f"VIOLATION: Faculty ID {fid} assigned {count} periods on {day} (max is 8)!"
        )


def test_subject_daily_and_weekly_constraints():
    """
    Requirement:
    - Each subject gets exactly 1 period per class per day.
    - Each subject gets exactly its configured periods_per_week allocated.
    """
    scheduler = TimetableScheduler()
    res = scheduler.generate()
    assert res["success"] is True

    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Check max 1 period per subject per class per day
    cursor.execute("""
        SELECT class_id, subject_id, day, COUNT(*) as count_per_day
        FROM timetable_entries
        GROUP BY class_id, subject_id, day
        HAVING count_per_day > 1;
    """)
    duplicate_days = cursor.fetchall()
    assert len(duplicate_days) == 0, f"Subject assigned more than once per day: {duplicate_days}"

    # 2. Check total periods per week matches subject.periods_per_week
    cursor.execute("""
        SELECT s.id, s.name, s.periods_per_week, COUNT(t.id) as scheduled_count
        FROM subjects s
        LEFT JOIN timetable_entries t ON s.id = t.subject_id
        GROUP BY s.id;
    """)
    subject_targets = [dict(r) for r in cursor.fetchall()]
    conn.close()

    for st in subject_targets:
        assert st["scheduled_count"] == st["periods_per_week"], (
            f"Subject '{st['name']}' has {st['scheduled_count']} periods scheduled, "
            f"expected exactly {st['periods_per_week']}!"
        )


def test_dynamic_regeneration_when_faculty_added():
    """
    Requirement: Timetable adjusts dynamically when faculty members change.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Add a new part-time faculty member
    cursor.execute("""
        INSERT INTO faculty (name, department, work_type, weekly_period_limit)
        VALUES ('Dr. Richard Feynman', 'Physics & Computing', 'part_time', 10);
    """)
    new_faculty_id = cursor.lastrowid

    # Add a subject taught by this new faculty
    cursor.execute("SELECT id FROM classes LIMIT 1;")
    cid = cursor.fetchone()["id"]
    cursor.execute("""
        INSERT INTO subjects (class_id, name, code, periods_per_week, faculty_id)
        VALUES (?, 'Quantum Algorithms', 'CS499', 3, ?);
    """, (cid, new_faculty_id))
    conn.commit()
    conn.close()

    # Regenerate timetable
    scheduler = TimetableScheduler()
    res = scheduler.generate()
    assert res["success"] is True

    # Verify that the new faculty was scheduled in periods 1..4 only
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT period_num FROM timetable_entries
        WHERE faculty_id = ?;
    """, (new_faculty_id,))
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 3, f"Expected 3 periods scheduled for Dr. Feynman, found {len(rows)}"
    for r in rows:
        assert r["period_num"] in PART_TIME_ALLOWED_PERIODS, (
            f"Dr. Feynman is part-time, but was scheduled in Period {r['period_num']}"
        )


def test_impossible_constraint_diagnostic_error():
    """
    Requirement: Scheduler handles errors gracefully with clear messages.
    If a subject requires more periods than days exist (e.g. 6 periods/week in 5-day week),
    or if total faculty capacity is insufficient, a clear SchedulingError is raised.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Temporarily set all faculty limits to 0 to simulate capacity deficit
    cursor.execute("UPDATE faculty SET weekly_period_limit = 0;")
    conn.commit()
    conn.close()

    scheduler = TimetableScheduler()
    with pytest.raises(SchedulingError) as exc_info:
        scheduler.generate()

    assert "capacity" in str(exc_info.value).lower() or "limit" in str(exc_info.value).lower()

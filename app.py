"""
Intelligent Department Timetable Scheduler - Flask Application

Stack: Flask (Python), SQLite, Vanilla HTML/CSS/JS.
Provides RESTful APIs with server-side validation, error handling,
automatic timetable regeneration on data mutations, and static web serving.
"""

import sqlite3
from typing import Dict, Any, Tuple
from flask import Flask, request, jsonify, render_template

from config import (
    DEFAULT_PART_TIME_WEEKLY_PERIODS,
    MAX_FULL_TIME_WEEKLY_PERIODS,
    WORK_TYPE_FULL_TIME,
    WORK_TYPE_PART_TIME,
    PART_TIME_ALLOWED_PERIODS,
    FULL_TIME_ALLOWED_PERIODS,
    PERIOD_TIMINGS,
    BREAK_TIMINGS,
    LUNCH_BREAK_START,
    LUNCH_BREAK_END,
    DAYS_OF_WEEK,
    TOTAL_PERIODS_PER_DAY,
    MIN_PERIODS_PER_WEEK,
    MAX_PERIODS_PER_WEEK,
)
from database import init_db, seed_sample_data_if_empty, get_db_connection
from scheduler import TimetableScheduler, SchedulingError

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Initialization Hooks
# ---------------------------------------------------------------------------
@app.before_request
def setup_if_needed():
    """Ensure database exists and seeds sample data on the first request."""
    if not hasattr(app, "_db_initialized"):
        init_db()
        seeded = seed_sample_data_if_empty()
        if seeded:
            try:
                TimetableScheduler().generate()
            except Exception:
                pass  # Seeded timetable will be regenerated on demand if needed
        app._db_initialized = True


# ---------------------------------------------------------------------------
# Helper: Safe Auto-Regeneration
# ---------------------------------------------------------------------------
def try_auto_regenerate() -> Tuple[bool, str]:
    """
    Attempts to automatically regenerate the timetable after data modifications.
    Returns (success, message).
    """
    try:
        scheduler = TimetableScheduler()
        res = scheduler.generate()
        return True, "Timetable regenerated successfully."
    except SchedulingError as se:
        return False, f"Data saved, but timetable regeneration note: {se.message}"
    except Exception as e:
        return False, "Data saved, but automatic timetable regeneration encountered an issue."


# ---------------------------------------------------------------------------
# Web Page Route
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Serves the main application dashboard."""
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Configuration API
# ---------------------------------------------------------------------------
@app.route("/api/config", methods=["GET"])
def get_config():
    """Returns timing constants, break definitions, and scheduling parameters."""
    return jsonify({
        "college_window": "09:00 AM - 04:45 PM",
        "total_periods": TOTAL_PERIODS_PER_DAY,
        "days": DAYS_OF_WEEK,
        "lunch_break": {
            "start": LUNCH_BREAK_START,
            "end": LUNCH_BREAK_END,
            "after_period": 4,
            "note": "Fixed lunch break as defined in project requirements"
        },
        "short_breaks": {
            "break_1": {"after_period": 2, "start": "10:40", "end": "10:50", "note": "Automatic placement between Period 2 & 3"},
            "break_2": {"after_period": 6, "start": "14:45", "end": "15:05", "note": "Automatic placement between Period 6 & 7"}
        },
        "part_time_window": {
            "start": "09:00",
            "end": "12:30",
            "periods": PART_TIME_ALLOWED_PERIODS,
            "default_weekly_limit": DEFAULT_PART_TIME_WEEKLY_PERIODS
        },
        "full_time_window": {
            "start": "09:00",
            "end": "16:45",
            "periods": FULL_TIME_ALLOWED_PERIODS,
            "default_weekly_limit": MAX_FULL_TIME_WEEKLY_PERIODS
        },
        "period_timings": PERIOD_TIMINGS,
        "break_timings": BREAK_TIMINGS
    })


# ---------------------------------------------------------------------------
# Classes / Sections APIs
# ---------------------------------------------------------------------------
@app.route("/api/classes", methods=["GET"])
def list_classes():
    """Returns all classes with their enrolled subjects and period counts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, 
               COUNT(s.id) AS subject_count,
               COALESCE(SUM(s.periods_per_week), 0) AS total_weekly_periods
        FROM classes c
        LEFT JOIN subjects s ON c.id = s.class_id
        GROUP BY c.id
        ORDER BY c.name;
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route("/api/classes", methods=["POST"])
def add_class():
    """Adds a new class and triggers automatic timetable regeneration."""
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    code = (data.get("code") or "").strip().upper()

    if not name or len(name) < 2:
        return jsonify({"error": "Class name is required (minimum 2 characters)."}), 400
    if not code or len(code) < 2:
        return jsonify({"error": "Class code is required (e.g. 'CSE-4A')."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO classes (name, code) VALUES (?, ?);", (name, code))
        new_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "A class with this name or code already exists."}), 400
    conn.close()

    regen_ok, regen_msg = try_auto_regenerate()
    return jsonify({
        "success": True,
        "id": new_id,
        "message": f"Class '{name}' created successfully.",
        "regeneration": {"success": regen_ok, "message": regen_msg}
    }), 201


@app.route("/api/classes/<int:class_id>", methods=["DELETE"])
def delete_class(class_id: int):
    """Deletes a class and cascade-deletes subjects and timetable entries."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM classes WHERE id = ?;", (class_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Class not found."}), 404

    class_name = row["name"]
    cursor.execute("DELETE FROM classes WHERE id = ?;", (class_id,))
    conn.commit()
    conn.close()

    regen_ok, regen_msg = try_auto_regenerate()
    return jsonify({
        "success": True,
        "message": f"Class '{class_name}' deleted.",
        "regeneration": {"success": regen_ok, "message": regen_msg}
    })


# ---------------------------------------------------------------------------
# Faculty Management APIs
# ---------------------------------------------------------------------------
@app.route("/api/faculty", methods=["GET"])
def list_faculty():
    """Returns all faculty with active timetable assigned period counts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT f.*,
               COUNT(t.id) AS assigned_periods
        FROM faculty f
        LEFT JOIN timetable_entries t ON f.id = t.faculty_id
        GROUP BY f.id
        ORDER BY f.name;
    """)
    faculty_list = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(faculty_list)


@app.route("/api/faculty", methods=["POST"])
def add_faculty():
    """
    Adds a new faculty member with validation and triggers automatic regeneration.
    Part-time faculty default to DEFAULT_PART_TIME_WEEKLY_PERIODS unless specified.
    """
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    department = (data.get("department") or "").strip()
    work_type = (data.get("work_type") or "").strip().lower()

    if not name:
        return jsonify({"error": "Faculty name is required."}), 400
    if not department:
        return jsonify({"error": "Department is required."}), 400
    if work_type not in (WORK_TYPE_FULL_TIME, WORK_TYPE_PART_TIME):
        return jsonify({"error": "Work type must be either 'full_time' or 'part_time'."}), 400

    # Determine weekly period limit
    limit_raw = data.get("weekly_period_limit")
    if limit_raw is not None and str(limit_raw).isdigit():
        weekly_limit = int(limit_raw)
    else:
        weekly_limit = (
            DEFAULT_PART_TIME_WEEKLY_PERIODS
            if work_type == WORK_TYPE_PART_TIME
            else MAX_FULL_TIME_WEEKLY_PERIODS
        )

    if weekly_limit < 1 or weekly_limit > 40:
        return jsonify({"error": "Weekly period limit must be between 1 and 40."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO faculty (name, department, work_type, weekly_period_limit)
        VALUES (?, ?, ?, ?);
    """, (name, department, work_type, weekly_limit))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()

    regen_ok, regen_msg = try_auto_regenerate()
    return jsonify({
        "success": True,
        "id": new_id,
        "message": f"Faculty '{name}' added successfully.",
        "regeneration": {"success": regen_ok, "message": regen_msg}
    }), 201


@app.route("/api/faculty/<int:faculty_id>", methods=["PUT"])
def update_faculty(faculty_id: int):
    """Updates an existing faculty member and triggers timetable regeneration."""
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    department = (data.get("department") or "").strip()
    work_type = (data.get("work_type") or "").strip().lower()

    if not name:
        return jsonify({"error": "Faculty name is required."}), 400
    if not department:
        return jsonify({"error": "Department is required."}), 400
    if work_type not in (WORK_TYPE_FULL_TIME, WORK_TYPE_PART_TIME):
        return jsonify({"error": "Work type must be either 'full_time' or 'part_time'."}), 400

    limit_raw = data.get("weekly_period_limit")
    if limit_raw is not None and str(limit_raw).isdigit():
        weekly_limit = int(limit_raw)
    else:
        weekly_limit = (
            DEFAULT_PART_TIME_WEEKLY_PERIODS
            if work_type == WORK_TYPE_PART_TIME
            else MAX_FULL_TIME_WEEKLY_PERIODS
        )

    if weekly_limit < 1 or weekly_limit > 40:
        return jsonify({"error": "Weekly period limit must be between 1 and 40."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM faculty WHERE id = ?;", (faculty_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Faculty member not found."}), 404

    cursor.execute("""
        UPDATE faculty
        SET name = ?, department = ?, work_type = ?, weekly_period_limit = ?
        WHERE id = ?;
    """, (name, department, work_type, weekly_limit, faculty_id))
    conn.commit()
    conn.close()

    regen_ok, regen_msg = try_auto_regenerate()
    return jsonify({
        "success": True,
        "message": f"Faculty '{name}' updated successfully.",
        "regeneration": {"success": regen_ok, "message": regen_msg}
    })


@app.route("/api/faculty/<int:faculty_id>", methods=["DELETE"])
def delete_faculty(faculty_id: int):
    """Deletes a faculty member and triggers automatic regeneration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM faculty WHERE id = ?;", (faculty_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Faculty member not found."}), 404

    faculty_name = row["name"]
    cursor.execute("DELETE FROM faculty WHERE id = ?;", (faculty_id,))
    conn.commit()
    conn.close()

    regen_ok, regen_msg = try_auto_regenerate()
    return jsonify({
        "success": True,
        "message": f"Faculty '{faculty_name}' removed.",
        "regeneration": {"success": regen_ok, "message": regen_msg}
    })


# ---------------------------------------------------------------------------
# Subject Management APIs
# ---------------------------------------------------------------------------
@app.route("/api/subjects", methods=["GET"])
def list_subjects():
    """Returns subjects, optionally filtered by class_id."""
    class_id = request.args.get("class_id")
    conn = get_db_connection()
    cursor = conn.cursor()

    base_query = """
        SELECT s.*, 
               c.name AS class_name, c.code AS class_code,
               f.name AS faculty_name, f.work_type AS faculty_work_type
        FROM subjects s
        JOIN classes c ON s.class_id = c.id
        LEFT JOIN faculty f ON s.faculty_id = f.id
    """
    params = []
    if class_id and class_id.isdigit():
        base_query += " WHERE s.class_id = ?"
        params.append(int(class_id))

    base_query += " ORDER BY c.name, s.name;"
    cursor.execute(base_query, params)
    subjects = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify(subjects)


@app.route("/api/subjects", methods=["POST"])
def add_subject():
    """
    Creates a new subject for a class and triggers automatic regeneration.
    Enforces periods_per_week between 1 and 5 (max 1 per day constraint).
    """
    data = request.get_json() or {}
    class_id = data.get("class_id")
    name = (data.get("name") or "").strip()
    code = (data.get("code") or "").strip().upper()
    periods_raw = data.get("periods_per_week")
    faculty_id = data.get("faculty_id")

    if not class_id:
        return jsonify({"error": "Class selection is required."}), 400
    if not name:
        return jsonify({"error": "Subject name is required."}), 400
    if not code:
        return jsonify({"error": "Subject code is required (e.g. 'CS201')."}), 400

    try:
        periods_per_week = int(periods_raw)
        if periods_per_week < MIN_PERIODS_PER_WEEK or periods_per_week > MAX_PERIODS_PER_WEEK:
            return jsonify({
                "error": f"Periods per week must be between {MIN_PERIODS_PER_WEEK} and {MAX_PERIODS_PER_WEEK}."
            }), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid periods per week value."}), 400

    # Optional faculty_id validation
    f_id_clean = None
    if faculty_id not in (None, "", "null", 0):
        try:
            f_id_clean = int(faculty_id)
        except ValueError:
            return jsonify({"error": "Invalid faculty ID."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify class exists
    cursor.execute("SELECT id FROM classes WHERE id = ?;", (class_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Specified class does not exist."}), 400

    # Verify faculty exists if provided
    if f_id_clean:
        cursor.execute("SELECT id FROM faculty WHERE id = ?;", (f_id_clean,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Specified faculty does not exist."}), 400

    try:
        cursor.execute("""
            INSERT INTO subjects (class_id, name, code, periods_per_week, faculty_id)
            VALUES (?, ?, ?, ?, ?);
        """, (class_id, name, code, periods_per_week, f_id_clean))
        new_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "A subject with this code already exists in this class."}), 400
    conn.close()

    regen_ok, regen_msg = try_auto_regenerate()
    return jsonify({
        "success": True,
        "id": new_id,
        "message": f"Subject '{name}' added successfully.",
        "regeneration": {"success": regen_ok, "message": regen_msg}
    }), 201


@app.route("/api/subjects/<int:subject_id>", methods=["PUT"])
def update_subject(subject_id: int):
    """Updates subject details and triggers automatic timetable regeneration."""
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    code = (data.get("code") or "").strip().upper()
    periods_raw = data.get("periods_per_week")
    faculty_id = data.get("faculty_id")

    if not name:
        return jsonify({"error": "Subject name is required."}), 400
    if not code:
        return jsonify({"error": "Subject code is required."}), 400

    try:
        periods_per_week = int(periods_raw)
        if periods_per_week < MIN_PERIODS_PER_WEEK or periods_per_week > MAX_PERIODS_PER_WEEK:
            return jsonify({
                "error": f"Periods per week must be between {MIN_PERIODS_PER_WEEK} and {MAX_PERIODS_PER_WEEK}."
            }), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid periods per week value."}), 400

    f_id_clean = None
    if faculty_id not in (None, "", "null", 0):
        try:
            f_id_clean = int(faculty_id)
        except ValueError:
            return jsonify({"error": "Invalid faculty ID."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, class_id FROM subjects WHERE id = ?;", (subject_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Subject not found."}), 404

    class_id = row["class_id"]

    try:
        cursor.execute("""
            UPDATE subjects
            SET name = ?, code = ?, periods_per_week = ?, faculty_id = ?
            WHERE id = ?;
        """, (name, code, periods_per_week, f_id_clean, subject_id))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Another subject with this code already exists in this class."}), 400
    conn.close()

    regen_ok, regen_msg = try_auto_regenerate()
    return jsonify({
        "success": True,
        "message": f"Subject '{name}' updated successfully.",
        "regeneration": {"success": regen_ok, "message": regen_msg}
    })


@app.route("/api/subjects/<int:subject_id>", methods=["DELETE"])
def delete_subject(subject_id: int):
    """Deletes a subject and triggers automatic timetable regeneration."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM subjects WHERE id = ?;", (subject_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Subject not found."}), 404

    subject_name = row["name"]
    cursor.execute("DELETE FROM subjects WHERE id = ?;", (subject_id,))
    conn.commit()
    conn.close()

    regen_ok, regen_msg = try_auto_regenerate()
    return jsonify({
        "success": True,
        "message": f"Subject '{subject_name}' deleted.",
        "regeneration": {"success": regen_ok, "message": regen_msg}
    })


# ---------------------------------------------------------------------------
# Timetable APIs
# ---------------------------------------------------------------------------
@app.route("/api/timetable", methods=["GET"])
def get_timetable():
    """
    Fetches the current timetable structured by class and day,
    along with break markers and faculty utilization statistics.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Load classes
    cursor.execute("SELECT * FROM classes ORDER BY id;")
    classes = [dict(r) for r in cursor.fetchall()]

    # Load timetable entries
    cursor.execute("""
        SELECT t.*, 
               s.name AS subject_name, s.code AS subject_code,
               f.name AS faculty_name, f.work_type AS faculty_work_type
        FROM timetable_entries t
        JOIN subjects s ON t.subject_id = s.id
        JOIN faculty f ON t.faculty_id = f.id
        ORDER BY t.class_id, t.day, t.period_num;
    """)
    entries = [dict(r) for r in cursor.fetchall()]

    # Load faculty stats
    cursor.execute("""
        SELECT f.id, f.name, f.work_type, f.weekly_period_limit,
               COUNT(t.id) AS assigned_periods
        FROM faculty f
        LEFT JOIN timetable_entries t ON f.id = t.faculty_id
        GROUP BY f.id
        ORDER BY f.name;
    """)
    faculty_stats = [dict(r) for r in cursor.fetchall()]
    conn.close()

    schedules_by_class: Dict[int, Dict[str, Any]] = {}
    for c in classes:
        schedules_by_class[c["id"]] = {
            "class_id": c["id"],
            "class_name": c["name"],
            "class_code": c["code"],
            "grid": {day: {} for day in DAYS_OF_WEEK},
        }

    for e in entries:
        cid = e["class_id"]
        day = e["day"]
        p = e["period_num"]
        if cid in schedules_by_class and day in schedules_by_class[cid]["grid"]:
            schedules_by_class[cid]["grid"][day][p] = {
                "period_num": p,
                "timing": PERIOD_TIMINGS.get(p, {}),
                "subject_id": e["subject_id"],
                "subject_name": e["subject_name"],
                "subject_code": e["subject_code"],
                "faculty_id": e["faculty_id"],
                "faculty_name": e["faculty_name"],
                "faculty_work_type": e["faculty_work_type"],
            }

    return jsonify({
        "total_classes": len(classes),
        "total_entries": len(entries),
        "schedules_by_class": schedules_by_class,
        "faculty_utilization": faculty_stats,
        "period_timings": PERIOD_TIMINGS,
        "break_timings": BREAK_TIMINGS,
        "days_of_week": DAYS_OF_WEEK,
    })


@app.route("/api/timetable/regenerate", methods=["POST"])
def manual_regenerate_timetable():
    """
    Manually triggers timetable regeneration and returns detailed diagnostics.
    """
    try:
        scheduler = TimetableScheduler()
        result = scheduler.generate()
        return jsonify(result)
    except SchedulingError as se:
        return jsonify({
            "success": False,
            "error": se.message,
            "details": se.details,
        }), 422
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred during timetable generation.",
        }), 500


# ---------------------------------------------------------------------------
# Global Error Handlers (Clean JSON responses, no tracebacks exposed)
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found_handler(e):
    return jsonify({"error": "The requested resource was not found."}), 404


@app.errorhandler(405)
def method_not_allowed_handler(e):
    return jsonify({"error": "HTTP method not allowed on this endpoint."}), 405


@app.errorhandler(500)
def server_error_handler(e):
    return jsonify({"error": "An internal server error occurred. Please verify your inputs."}), 500


if __name__ == "__main__":
    # Local development server
    init_db()
    seed_sample_data_if_empty()
    try:
        TimetableScheduler().generate()
    except Exception:
        pass
    print("Intelligent Department Timetable Scheduler running at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)

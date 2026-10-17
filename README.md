# 🎓 Intelligent Department Timetable Scheduler

An automated, conflict-free timetable scheduling system for academic departments covering **multiple classes/sections**, a **shared faculty pool**, **strict working windows**, **load limits**, and **automatic break placements**.

Built with **Flask (Python)**, **SQLite**, and **vanilla HTML/CSS/JavaScript**.

---

## 🌟 Why This Stack Suits a College Project & Viva

1. **Minimal Footprint & Zero Bloat:** Unlike heavy Node/Webpack setups or full-scale enterprise frameworks, Flask + SQLite runs out of the box with virtually zero dependency baggage.
2. **Deterministic & Easy to Run Locally:** A single `python app.py` command boots the entire server and SQLite database without needing external database engines (PostgreSQL/MySQL) or background workers.
3. **Crystal-Clear Viva Explanation:** 
   - **Data Layer:** SQLite provides clean relational schema tables (`classes`, `faculty`, `subjects`, `timetable_entries`) with ACID integrity and foreign keys.
   - **Scheduling Engine:** Pure Python implementation of a **Constraint Satisfaction Problem (CSP)** with **Minimum Remaining Values (MRV)** heuristic — easy to draw and explain on a whiteboard during project viva.
   - **Presentation Layer:** Vanilla HTML5, modern CSS custom properties, and ES6+ JavaScript without build-step obscurity.

---

## ⏰ Working Windows, Constants & Break Architecture

The college timetable adheres strictly to the following parameters defined in [`config.py`](file:///d:/barathi%20files/config.py):

| Parameter | Configuration Value | Constant Name in Code | Description |
|---|---|---|---|
| **College Operating Hours** | `09:00 AM - 04:45 PM` | `COLLEGE_START_TIME`, `COLLEGE_END_TIME` | Total daily window: 465 minutes. |
| **Total Periods per Day** | `8 Periods` (50 min each) | `TOTAL_PERIODS_PER_DAY` | Periods 1 through 8. |
| **Fixed Lunch Break** | `12:30 PM - 01:05 PM` (35 min) | `LUNCH_BREAK_START`, `LUNCH_BREAK_END` | **Fixed constant**; occurs consistently after Period 4 across all classes. |
| **Short Break 1 (Morning)** | `10:40 AM - 10:50 AM` (10 min) | `SHORT_BREAK_1_AFTER_PERIOD = 2` | **Automatically placed** between Period 2 and Period 3. |
| **Short Break 2 (Tea Break)** | `02:45 PM - 03:05 PM` (20 min) | `SHORT_BREAK_2_AFTER_PERIOD = 6` | **Automatically placed** between Period 6 and Period 7. |
| **Full-Time Window** | `09:00 AM - 04:45 PM` | `FULL_TIME_ALLOWED_PERIODS = [1..8]` | Full-time faculty are eligible for all 8 periods (max 8/day). |
| **Part-Time Window** | `09:00 AM - 12:30 PM` | `PART_TIME_ALLOWED_PERIODS = [1..4]` | Fixed half-day window. **No time extensions permitted**. |
| **Part-Time Weekly Limit Default** | `12 periods / week` | `DEFAULT_PART_TIME_WEEKLY_PERIODS` | Serves as the system default, but configured and stored per faculty member in SQLite. |

### Daily Period-by-Period Timeline:
```
09:00 - 09:50  | Period 1 (50m)  [Full-Time & Part-Time]
09:50 - 10:40  | Period 2 (50m)  [Full-Time & Part-Time]
10:40 - 10:50  | Morning Break (10m) [AUTOMATIC PLACEMENT]
10:50 - 11:40  | Period 3 (50m)  [Full-Time & Part-Time]
11:40 - 12:30  | Period 4 (50m)  [Full-Time & Part-Time]
12:30 - 13:05  | Lunch Break (35m)   [FIXED CONSTANT]
13:05 - 13:55  | Period 5 (50m)  [Full-Time Only]
13:55 - 14:45  | Period 6 (50m)  [Full-Time Only]
14:45 - 15:05  | Tea Break (20m)     [AUTOMATIC PLACEMENT]
15:05 - 15:55  | Period 7 (50m)  [Full-Time Only]
15:55 - 16:45  | Period 8 (50m)  [Full-Time Only]
```

---

## 🧠 Scheduling Algorithm & Intelligence

The core scheduler in [`scheduler.py`](file:///d:/barathi%20files/scheduler.py) models timetable generation as a **Constraint Satisfaction Problem (CSP)** solved via **Backtracking with Heuristics**:

1. **Single Booking Invariant:** For any given `(day, period)`, a faculty member is assigned to at most 1 class.
2. **Subject Daily Frequency:** Each subject gets **exactly 1 period per class per day** (no same-day duplicates).
3. **Subject Weekly Allocation:** Each subject receives exactly `subject.periods_per_week` periods (1 to 5) across distinct days of the week.
4. **Strict Working Windows:**
   - Full-time faculty may be scheduled in Periods 1 through 8.
   - Part-time faculty are strictly restricted to Periods 1 through 4 (9:00 AM - 12:30 PM). The scheduler **never extends or stretches** their hours.
5. **Load Caps:**
   - Full-time faculty: at most 8 periods per day.
   - Part-time faculty: at most their configured `weekly_period_limit` per week.
6. **Open Faculty Pool:** Any part-time or full-time faculty member may teach any subject; if a subject has a designated teacher, they are assigned to it; if unassigned, any available qualified faculty from the shared pool is assigned.
7. **Automatic Regeneration:** Whenever faculty members or subjects are added, modified, or removed, the timetable automatically recalculates conflict-free allocations. If constraints are mathematically impossible, an informative diagnostic warning is returned without crashing.

---

## 📁 Project Structure

```
d:/barathi files/
├── app.py                  # Flask web server, REST API endpoints, input validation
├── config.py               # Named constants, operating windows, break timings
├── database.py             # SQLite database layer, schema initialization, seed data
├── scheduler.py            # Intelligent CSP backtracking scheduler & diagnostics
├── requirements.txt        # Python package dependencies (Flask, pytest)
├── README.md               # Documentation & viva presentation guide
├── static/
│   ├── css/
│   │   └── style.css       # Clean, modern stylesheet with responsive design & print mode
│   └── js/
│       └── app.js          # Vanilla JS dashboard interactions, modals, and API calls
├── templates/
│   └── index.html          # Clean single-page application dashboard
└── tests/
    ├── __init__.py
    └── test_scheduler.py   # Automated pytest suite testing all required invariants
```

---

## 🚀 Quick Setup & How to Run Locally

### 1. Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- `pip` (Python package manager)

### 2. Install Dependencies
Open PowerShell or Terminal in the project root:
```powershell
pip install -r requirements.txt
```

### 3. Run the Application
```powershell
python app.py
```
Open your browser and navigate to:
**`http://127.0.0.1:5000`**

*Note: On initial startup, the database is automatically created and populated with sample classes (`CSE-2A`, `CSE-2B`, `CSE-3A`), faculty members (full-time and part-time), and subjects with pre-calculated conflict-free schedules.*

---

## 🧪 Running Automated Tests

Run the test suite using `pytest`:
```powershell
pytest tests/ -v
```

The test suite automatically tests:
- **`test_no_faculty_double_booking`**: Confirms zero faculty overlapping across classes in the same period.
- **`test_breaks_and_period_timings_respected`**: Confirms fixed lunch break (12:30 - 1:05 PM) and automatic placement of short breaks.
- **`test_faculty_windows_and_load_limits`**: Confirms part-time faculty are never assigned in periods 5-8, and weekly caps are respected.
- **`test_subject_daily_and_weekly_constraints`**: Confirms at most 1 period per subject per class per day, and weekly quotas matched.
- **`test_dynamic_regeneration_when_faculty_added`**: Confirms automatic schedule regeneration on data changes.
- **`test_impossible_constraint_diagnostic_error`**: Confirms graceful error reporting when constraints cannot be satisfied.

---

## 🎤 Project Viva / Oral Exam Q&A Guide

**Q1: How does the system prevent faculty double-booking across sections?**
> *Answer:* The scheduler tracks assignments using a lookup hash map keyed by `(faculty_id, day, period)`. Before assigning any slot, it checks whether the faculty member is already committed in that slot for any other class. If so, that candidate slot is rejected during backtracking.

**Q2: How is the part-time faculty window enforced without stretching hours?**
> *Answer:* In `config.py`, `PART_TIME_ALLOWED_PERIODS = [1, 2, 3, 4]` maps directly to 9:00 AM - 12:30 PM. When generating candidate slots for a part-time faculty member, the period domain is strictly restricted to `[1, 2, 3, 4]`. Periods 5 through 8 (1:05 PM - 4:45 PM) are mathematically excluded from the variable domain.

**Q3: How are the breaks handled?**
> *Answer:* 
> 1. The **Lunch Break** is a fixed named constant (`12:30 PM to 1:05 PM`) placed after Period 4.
> 2. The **Two Short Breaks** are placed automatically: Morning Break after Period 2 (10:40 - 10:50 AM) and Afternoon Tea Break after Period 6 (2:45 - 3:05 PM), dividing each half of the day into balanced 2-period learning blocks.

**Q4: What happens if an impossible constraint is entered (e.g. deleting all faculty)?**
> *Answer:* The scheduler executes pre-flight feasibility validation. If required subject periods exceed available faculty capacity, a custom `SchedulingError` is raised with a clear diagnostic message. The database transaction is rolled back, preventing corrupted schedules, and the UI displays an actionable warning.

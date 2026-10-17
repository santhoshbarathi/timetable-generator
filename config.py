"""
Intelligent Department Timetable Scheduler - Configuration Constants

College Day Window: 9:00 AM - 4:45 PM (8 periods per day)
Breaks:
  - 1 Fixed Lunch Break: 12:30 PM - 1:05 PM (35 minutes)
  - 2 Short Breaks: Placed automatically between periods (10 min after P2, 20 min after P6)
"""

# College Operating Window
COLLEGE_START_TIME = "09:00"
COLLEGE_END_TIME = "16:45"
TOTAL_PERIODS_PER_DAY = 8
DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# Fixed Lunch Break (As specified in project requirements: 12:30 PM to 1:05 PM)
LUNCH_BREAK_START = "12:30"
LUNCH_BREAK_END = "13:05"
LUNCH_BREAK_AFTER_PERIOD = 4  # Period 4 ends at 12:30 PM; Lunch is 12:30 PM - 1:05 PM

# Automatic Short Break Placements
# Short Break 1: Placed between Period 2 and Period 3 (10:40 AM - 10:50 AM)
# Short Break 2: Placed between Period 6 and Period 7 (02:45 PM - 03:05 PM)
SHORT_BREAK_1_AFTER_PERIOD = 2
SHORT_BREAK_2_AFTER_PERIOD = 6

# Period Time Definitions (50 minutes per period)
# Total day = 465 minutes (9:00 AM to 4:45 PM)
# Periods = 8 * 50 = 400 min
# Lunch = 35 min
# Short breaks = 10 min + 20 min = 30 min
# 400 + 35 + 30 = 465 min (Exact match)
PERIOD_TIMINGS = {
    1: {"start": "09:00", "end": "09:50", "label": "09:00 - 09:50"},
    2: {"start": "09:50", "end": "10:40", "label": "09:50 - 10:40"},
    3: {"start": "10:50", "end": "11:40", "label": "10:50 - 11:40"},
    4: {"start": "11:40", "end": "12:30", "label": "11:40 - 12:30"},
    5: {"start": "13:05", "end": "13:55", "label": "01:05 - 01:55"},
    6: {"start": "13:55", "end": "14:45", "label": "01:55 - 02:45"},
    7: {"start": "15:05", "end": "15:55", "label": "03:05 - 03:55"},
    8: {"start": "15:55", "end": "16:45", "label": "03:55 - 04:45"},
}

BREAK_TIMINGS = {
    "short_break_1": {
        "name": "Morning Break",
        "after_period": SHORT_BREAK_1_AFTER_PERIOD,
        "start": "10:40",
        "end": "10:50",
        "duration_minutes": 10,
        "type": "automatic_short_break",
    },
    "lunch_break": {
        "name": "Lunch Break",
        "after_period": LUNCH_BREAK_AFTER_PERIOD,
        "start": LUNCH_BREAK_START,
        "end": LUNCH_BREAK_END,
        "duration_minutes": 35,
        "type": "fixed_lunch_break",
    },
    "short_break_2": {
        "name": "Afternoon Tea Break",
        "after_period": SHORT_BREAK_2_AFTER_PERIOD,
        "start": "14:45",
        "end": "15:05",
        "duration_minutes": 20,
        "type": "automatic_short_break",
    },
}

# Faculty Work Types & Working Windows
WORK_TYPE_FULL_TIME = "full_time"
WORK_TYPE_PART_TIME = "part_time"

# Full-time faculty: 9:00 AM - 4:45 PM (All 8 periods eligible, up to 8 periods/day)
FULL_TIME_WINDOW_START = "09:00"
FULL_TIME_WINDOW_END = "16:45"
FULL_TIME_ALLOWED_PERIODS = [1, 2, 3, 4, 5, 6, 7, 8]
MAX_FULL_TIME_DAILY_PERIODS = 8
MAX_FULL_TIME_WEEKLY_PERIODS = 40

# Part-time faculty: Fixed half-day window (9:00 AM - 12:30 PM, Periods 1 through 4)
# Requirement: No time extensions under any circumstances.
PART_TIME_WINDOW_START = "09:00"
PART_TIME_WINDOW_END = "12:30"
PART_TIME_ALLOWED_PERIODS = [1, 2, 3, 4]

# Default part-time weekly period count constant
# Serves as the initial default, but each faculty member has this stored individually in the database.
DEFAULT_PART_TIME_WEEKLY_PERIODS = 12

# Subject Constraints
MIN_PERIODS_PER_WEEK = 1
MAX_PERIODS_PER_WEEK = 6  # Up to 6 periods per week per theory subject
MAX_SUBJECT_PERIODS_PER_DAY = 2  # Up to 2 periods of the same subject on any day (e.g. 6-period subjects or 2-hour labs)


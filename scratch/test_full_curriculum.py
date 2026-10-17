"""
Populate and test full 40-period curriculum for all 7 classes.
"""

import sys
sys.path.insert(0, '.')
from scratch.test_scheduler_engine import solve_timetable
import sqlite3

def run():
    conn = sqlite3.connect('scheduler.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM classes ORDER BY id')
    classes = [dict(r) for r in c.fetchall()]
    c.execute('SELECT * FROM faculty ORDER BY id')
    faculty = [dict(r) for r in c.fetchall()]
    c.execute('SELECT * FROM subjects ORDER BY id')
    subjects = [dict(r) for r in c.fetchall()]
    conn.close()
    
    print(f"Loaded {len(classes)} classes, {len(faculty)} faculty, {len(subjects)} subjects")
    res = solve_timetable(classes, faculty, subjects)
    if res:
        print(f"Total entries scheduled: {len(res)}")
    else:
        print("Solve returned None")

if __name__ == '__main__':
    run()

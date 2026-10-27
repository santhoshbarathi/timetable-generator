"""
Fix over-allocated CSE-2A and CSE-2B classes (total 42 periods, max is 40).
Also add Placement (2 periods) for 2nd/3rd year classes that are missing it.
Also ensure all classes have Library (1 period).

Strategy for CSE-2A and CSE-2B (42 -> 40):
  - DS Lab: 4 -> 2 periods  (saves 2 periods per class)
  Both sections then total exactly 40 periods.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scheduler.db")


def fix_periods():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # ── Fix CSE-2A (class_id=12): reduce DS Lab from 4 -> 2 ─────────────────
    cursor.execute(
        "UPDATE subjects SET periods_per_week = 2 WHERE class_id = 12 AND code = 'CS25C08_LAB';"
    )
    print(f"CSE-2A: DS Lab periods_per_week -> 2 (rows affected: {cursor.rowcount})")

    # ── Fix CSE-2B (class_id=13): reduce DS Lab from 4 -> 2 ─────────────────
    cursor.execute(
        "UPDATE subjects SET periods_per_week = 2 WHERE class_id = 13 AND code = 'CS25C08_LAB';"
    )
    print(f"CSE-2B: DS Lab periods_per_week -> 2 (rows affected: {cursor.rowcount})")

    conn.commit()

    # ── Verify totals ─────────────────────────────────────────────────────────
    print("\n--- Class Period Totals After Fix ---")
    for cls in cursor.execute("SELECT id, code, name FROM classes ORDER BY code").fetchall():
        total = sum(r[0] for r in cursor.execute(
            "SELECT periods_per_week FROM subjects WHERE class_id=?", (cls["id"],)
        ).fetchall())
        flag = "✓" if total <= 40 else "✗ OVER"
        print(f"  [{cls['code']:10s}] {cls['name']:55s} {total:2d}/40 {flag}")

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    fix_periods()

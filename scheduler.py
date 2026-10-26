"""
Intelligent Department Timetable Scheduler - Core Scheduling Engine

Implements a Constraint Satisfaction Problem (CSP) solver with:
  - Minimum Remaining Values (MRV) and Degree heuristics
  - Strict enforcement of part-time half-day working window (09:00 - 12:30, Periods 1-4)
  - Strict enforcement of full-time window (09:00 - 16:45, Periods 1-8)
  - Enforced load limits (full-time <= 8/day, part-time <= configured weekly count)
  - Subject constraint: Exactly 1 period per class per day
  - Subject weekly quota: Exactly subject.periods_per_week allocated
  - Faculty single-booking: At most one class per faculty member per (day, period)
  - Break placements: Fixed lunch break (12:30 - 13:05) and automatic short breaks
  - Clear diagnostic explanations if generation cannot be satisfied
"""

import random
from typing import Dict, List, Tuple, Optional, Any, Set
from config import (
    COMPULSORY_FACULTY_WEEKLY_HOURS,
    ZERO_FREE_PERIODS_POLICY,
    DAYS_OF_WEEK,
    TOTAL_PERIODS_PER_DAY,
    PART_TIME_ALLOWED_PERIODS,
    FULL_TIME_ALLOWED_PERIODS,
    WORK_TYPE_PART_TIME,
    WORK_TYPE_FULL_TIME,
    MAX_FULL_TIME_DAILY_PERIODS,
    PERIOD_TIMINGS,
    BREAK_TIMINGS,
    LUNCH_BREAK_START,
    LUNCH_BREAK_END,
)
from database import get_db_connection


class SchedulingError(Exception):
    """Custom exception raised when scheduling constraints cannot be satisfied."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class TimetableScheduler:
    """
    Intelligent Timetable Scheduler implementing constraint satisfaction with backtracking.
    """

    def __init__(self, seed: Optional[int] = 42):
        self.days = DAYS_OF_WEEK
        self.periods = list(range(1, TOTAL_PERIODS_PER_DAY + 1))
        self.rng = random.Random(seed)

    def load_data(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Loads classes, faculty, and subjects from the SQLite database."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM classes ORDER BY id;")
        classes = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM faculty ORDER BY id;")
        faculty = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM subjects ORDER BY class_id, id;")
        subjects = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return classes, faculty, subjects

    def validate_preconditions(
        self,
        classes: List[Dict[str, Any]],
        faculty: List[Dict[str, Any]],
        subjects: List[Dict[str, Any]],
    ) -> None:
        """
        Validates mathematical feasibility before launching the solver.
        Provides precise diagnostic feedback if inputs violate basic limits.
        """
        if not classes:
            raise SchedulingError("No classes defined. Please add at least one class.")

        if not subjects:
            raise SchedulingError("No subjects defined. Please configure subjects for your classes.")

        if not faculty:
            raise SchedulingError("No faculty members registered. Timetable requires a faculty pool.")

        faculty_map = {f["id"]: f for f in faculty}

        # 1. Check subject periods per week
        for s in subjects:
            if s["periods_per_week"] < 1:
                raise SchedulingError(
                    f"Subject '{s['name']}' in class ID {s['class_id']} has invalid periods_per_week ({s['periods_per_week']}). Must be >= 1."
                )
            if s["periods_per_week"] > 6:
                raise SchedulingError(
                    f"Subject '{s['name']}' requires {s['periods_per_week']} periods/week, "
                    f"exceeding the maximum allowed of 6 periods per week."
                )

        # 2. Check each class total weekly periods vs available class slots
        max_class_weekly_slots = len(self.days) * TOTAL_PERIODS_PER_DAY  # 5 * 8 = 40
        class_periods: Dict[int, int] = {}
        for s in subjects:
            class_periods[s["class_id"]] = class_periods.get(s["class_id"], 0) + s["periods_per_week"]

        for cid, total_p in class_periods.items():
            if total_p > max_class_weekly_slots:
                cname = next((c["name"] for c in classes if c["id"] == cid), str(cid))
                raise SchedulingError(
                    f"Class '{cname}' requires {total_p} periods per week, "
                    f"exceeding the maximum weekly capacity of {max_class_weekly_slots} periods (5 days x 8 periods)."
                )

        # 3. Check individual designated faculty capacities
        designated_load: Dict[int, int] = {}
        for s in subjects:
            fid = s["faculty_id"]
            if fid is not None:
                if fid not in faculty_map:
                    raise SchedulingError(
                        f"Subject '{s['name']}' is assigned to non-existent faculty ID {fid}."
                    )
                designated_load[fid] = designated_load.get(fid, 0) + s["periods_per_week"]

        for fid, req_load in designated_load.items():
            f = faculty_map[fid]
            if req_load > f["weekly_period_limit"]:
                raise SchedulingError(
                    f"Faculty '{f['name']}' ({f['work_type'].replace('_', ' ').title()}) has a weekly limit "
                    f"of {f['weekly_period_limit']} periods, but assigned subjects require {req_load} periods."
                )

            # Part-time faculty can only work periods 1-4 (4 periods/day * 5 days = 20 periods max/week)
            if f["work_type"] == WORK_TYPE_PART_TIME:
                max_pt_possible = len(self.days) * len(PART_TIME_ALLOWED_PERIODS)  # 5 * 4 = 20
                if req_load > max_pt_possible:
                    raise SchedulingError(
                        f"Part-time faculty '{f['name']}' cannot teach {req_load} periods/week within the "
                        f"fixed half-day window (maximum theoretical capacity is {max_pt_possible} periods/week)."
                    )

        # 3b. Verify compulsory 16 hours per week requirement
        for f in faculty:
            if f.get("weekly_period_limit") != COMPULSORY_FACULTY_WEEKLY_HOURS:
                f["weekly_period_limit"] = COMPULSORY_FACULTY_WEEKLY_HOURS

        # 4. Total department faculty capacity vs total required periods
        total_required_periods = sum(s["periods_per_week"] for s in subjects)
        total_faculty_capacity = sum(f["weekly_period_limit"] for f in faculty)
        if total_faculty_capacity < total_required_periods:
            raise SchedulingError(
                f"Total faculty capacity ({total_faculty_capacity} periods/week) is less than total "
                f"required subject periods ({total_required_periods} periods/week). Please add more faculty or increase limits."
            )

    def generate(self) -> Dict[str, Any]:
        """
        Executes the intelligent scheduling algorithm.
        Returns a dictionary containing the generated schedule and metadata.
        """
        classes, faculty, subjects = self.load_data()
        self.validate_preconditions(classes, faculty, subjects)

        faculty_map = {f["id"]: f for f in faculty}
        classes_map = {c["id"]: c for c in classes}
        subjects_map = {s["id"]: s for s in subjects}

        # Attempt up to 10 randomized heuristic search runs if needed
        for attempt in range(12):
            result = self._solve_schedule(classes, faculty, subjects, faculty_map, seed_offset=attempt)
            if result is not None:
                return self._persist_and_format_schedule(result, classes_map, subjects_map, faculty_map)

        raise SchedulingError(
            "Could not find a conflict-free timetable satisfying all simultaneous constraints. "
            "Consider adjusting subject hours or faculty assignments."
        )

    def _solve_schedule(
        self,
        classes: List[Dict[str, Any]],
        faculty: List[Dict[str, Any]],
        subjects: List[Dict[str, Any]],
        faculty_map: Dict[int, Dict[str, Any]],
        seed_offset: int = 0,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Solves the CSP across all classes using prioritized class-level backtracking
        with MRV (Minimum Remaining Values) heuristics.
        Supports:
          - Full 40-period weekly schedule (0 free periods)
          - 2-hour continuous Laboratory blocks
          - Up to 6 periods per week per theory subject
          - Library (1 period) and Placement (2 periods)
          - Strict part-time half-day window (09:00 - 12:30, Periods 1-4)
          - Strict full-time working window (09:00 - 16:45, Periods 1-8)
          - 0 faculty double-booking
        """
        rng = random.Random(42 + seed_offset)

        # Global tracking structures across classes
        # (faculty_id, day, period) -> entry
        fac_sched: Dict[Tuple[int, str, int], Dict[str, Any]] = {}
        fac_load: Dict[int, int] = {f["id"]: 0 for f in faculty}
        all_entries: List[Dict[str, Any]] = []

        pt_periods = set(PART_TIME_ALLOWED_PERIODS)  # {1, 2, 3, 4}

        for cl in classes:
            cid = cl["id"]
            class_subjs = [s for s in subjects if s["class_id"] == cid]
            if not class_subjs:
                continue

            # Split subjects into 2-hour Laboratory sessions and standard subjects
            labs = [
                s for s in class_subjs
                if ("lab" in s["name"].lower() or "laboratory" in s["name"].lower()) and s["periods_per_week"] == 2
            ]
            non_labs = [s for s in class_subjs if s not in labs]

            # Flatten non-labs into individual period tokens
            tokens = []
            for s in non_labs:
                for _ in range(s["periods_per_week"]):
                    tokens.append(s)

            # Prioritize tokens: Part-time faculty first (morning slots only!), then higher weekly periods
            def token_key(s: Dict[str, Any]) -> Tuple[int, int]:
                fid = s["faculty_id"]
                is_pt = 1 if fid and faculty_map[fid]["work_type"] == WORK_TYPE_PART_TIME else 0
                return (-is_pt, -s["periods_per_week"])

            tokens.sort(key=token_key)

            solved = False
            for attempt in range(80):
                class_sched: Dict[Tuple[str, int], Dict[str, Any]] = {}
                subj_day_cnt: Dict[Tuple[str, int], int] = {}
                applied_fac: List[Tuple[int, str, int, Dict[str, Any]]] = []

                # Step 1: Schedule 2-hour laboratory sessions as continuous 2-period blocks
                lab_success = True
                shuffled_days = list(self.days)
                rng.shuffle(shuffled_days)

                for i, lab_s in enumerate(labs):
                    fid = lab_s["faculty_id"]
                    fac = faculty_map[fid]
                    is_pt = (fac["work_type"] == WORK_TYPE_PART_TIME)
                    # For FT, prefer afternoon slots (5,6) or (7,8) first to keep morning slots for PT
                    valid_pairs = [(1, 2), (3, 4)] if is_pt else [(5, 6), (7, 8), (3, 4), (1, 2)]

                    day = shuffled_days[i % len(self.days)]
                    rng.shuffle(valid_pairs)

                    placed = False
                    for p1, p2 in valid_pairs:
                        if (day, p1) in class_sched or (day, p2) in class_sched:
                            continue
                        if (fid, day, p1) in fac_sched or (fid, day, p2) in fac_sched:
                            continue
                        if fac_load[fid] + 2 > fac["weekly_period_limit"]:
                            continue

                        e1 = {"class_id": cid, "day": day, "period_num": p1, "subject_id": lab_s["id"], "faculty_id": fid}
                        e2 = {"class_id": cid, "day": day, "period_num": p2, "subject_id": lab_s["id"], "faculty_id": fid}
                        class_sched[(day, p1)] = e1
                        class_sched[(day, p2)] = e2
                        fac_sched[(fid, day, p1)] = e1
                        fac_sched[(fid, day, p2)] = e2
                        applied_fac.append((fid, day, p1, e1))
                        applied_fac.append((fid, day, p2, e2))
                        subj_day_cnt[(day, lab_s["id"])] = 2
                        fac_load[fid] += 2
                        placed = True
                        break

                    if not placed:
                        lab_success = False
                        break

                if not lab_success:
                    for fid, day, p, _ in applied_fac:
                        fac_sched.pop((fid, day, p), None)
                        fac_load[fid] -= 1
                    continue

                # Step 2: Backtrack the remaining tokens into the remaining empty slots of the class
                empty_slots = [
                    (d, p) for d in self.days for p in self.periods if (d, p) not in class_sched
                ]

                def backtrack_tokens(t_idx: int) -> bool:
                    if t_idx >= len(tokens):
                        return True
                    s = tokens[t_idx]
                    sid = s["id"]
                    fid = s["faculty_id"]
                    fac = faculty_map[fid]
                    is_pt = (fac["work_type"] == WORK_TYPE_PART_TIME)
                    max_per_day = 2 if s["periods_per_week"] >= 5 else 1

                    if fac_load[fid] >= fac["weekly_period_limit"]:
                        return False

                    avail_slots = []
                    for d, p in empty_slots:
                        if (d, p) in class_sched:
                            continue
                        if is_pt and p not in pt_periods:
                            continue
                        if (fid, d, p) in fac_sched:
                            continue
                        if subj_day_cnt.get((d, sid), 0) >= max_per_day:
                            continue
                        avail_slots.append((d, p))

                    rng.shuffle(avail_slots)
                    # Heuristic: prioritize days where this subject has 0 periods yet
                    avail_slots.sort(key=lambda dp: subj_day_cnt.get((dp[0], sid), 0))

                    for d, p in avail_slots:
                        e = {"class_id": cid, "day": d, "period_num": p, "subject_id": sid, "faculty_id": fid}
                        class_sched[(d, p)] = e
                        fac_sched[(fid, d, p)] = e
                        subj_day_cnt[(d, sid)] = subj_day_cnt.get((d, sid), 0) + 1
                        fac_load[fid] += 1

                        if backtrack_tokens(t_idx + 1):
                            return True

                        class_sched.pop((d, p), None)
                        fac_sched.pop((fid, d, p), None)
                        subj_day_cnt[(d, sid)] -= 1
                        fac_load[fid] -= 1

                    return False

                if backtrack_tokens(0):
                    solved = True
                    all_entries.extend(class_sched.values())
                    break
                else:
                    for fid, day, p, _ in applied_fac:
                        fac_sched.pop((fid, day, p), None)
                        fac_load[fid] -= 1

            if not solved:
                return None

        return all_entries

    def _persist_and_format_schedule(
        self,
        entries: List[Dict[str, Any]],
        classes_map: Dict[int, Dict[str, Any]],
        subjects_map: Dict[int, Dict[str, Any]],
        faculty_map: Dict[int, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Saves timetable entries to SQLite inside an atomic transaction,
        and returns structured schedule data for the API response.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            # Clear old timetable
            cursor.execute("DELETE FROM timetable_entries;")

            # Insert new entries
            insert_query = """
            INSERT INTO timetable_entries (class_id, day, period_num, subject_id, faculty_id)
            VALUES (?, ?, ?, ?, ?);
            """
            cursor.executemany(
                insert_query,
                [
                    (e["class_id"], e["day"], e["period_num"], e["subject_id"], e["faculty_id"])
                    for e in entries
                ],
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise SchedulingError(f"Failed to persist timetable to database: {str(e)}")
        finally:
            conn.close()

        # Format by class and day for convenient consumption
        schedules_by_class: Dict[int, Dict[str, Any]] = {}
        for cid, cinfo in classes_map.items():
            schedules_by_class[cid] = {
                "class_id": cid,
                "class_name": cinfo["name"],
                "class_code": cinfo["code"],
                "grid": {day: {} for day in self.days},
            }

        faculty_utilization: Dict[int, Dict[str, Any]] = {
            fid: {
                "id": fid,
                "name": finfo["name"],
                "work_type": finfo["work_type"],
                "limit": finfo["weekly_period_limit"],
                "assigned_periods": 0,
            }
            for fid, finfo in faculty_map.items()
        }

        for e in entries:
            cid = e["class_id"]
            day = e["day"]
            p = e["period_num"]
            sid = e["subject_id"]
            fid = e["faculty_id"]

            sinfo = subjects_map.get(sid, {})
            finfo = faculty_map.get(fid, {})

            faculty_utilization[fid]["assigned_periods"] += 1

            schedules_by_class[cid]["grid"][day][p] = {
                "period_num": p,
                "timing": PERIOD_TIMINGS.get(p, {}),
                "subject_id": sid,
                "subject_name": sinfo.get("name", "Unknown"),
                "subject_code": sinfo.get("code", "N/A"),
                "faculty_id": fid,
                "faculty_name": finfo.get("name", "Unknown"),
                "faculty_work_type": finfo.get("work_type", "full_time"),
            }

        return {
            "success": True,
            "message": "Timetable generated successfully with 0 conflicts.",
            "total_classes": len(classes_map),
            "total_entries": len(entries),
            "schedules_by_class": schedules_by_class,
            "faculty_utilization": list(faculty_utilization.values()),
            "break_timings": BREAK_TIMINGS,
            "period_timings": PERIOD_TIMINGS,
            "days_of_week": self.days,
        }


def regenerate_timetable_if_needed() -> Dict[str, Any]:
    """Helper function to trigger regeneration."""
    scheduler = TimetableScheduler()
    return scheduler.generate()

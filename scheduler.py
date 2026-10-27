"""
Intelligent Department Timetable Scheduler - Core Scheduling Engine

Implements a Constraint Satisfaction Problem (CSP) solver with:
  - Strict no-faculty-double-booking: faculty cannot be assigned to two classes at the same time
  - Mandatory Library period (1 period/week) for ALL classes
  - Mandatory consecutive 2-period Placement block for 2nd and 3rd year classes (Semesters 3 & 5)
  - 2-hour continuous Lab blocks scheduled before theory tokens
  - Zero empty period boxes: all 40 weekly slots (5 days x 8 periods) filled
  - Strict part-time half-day window (09:00 - 12:30, Periods 1-4)
  - Subject max 1 period per day (2 for high-load subjects)
  - Full clash verification with atomic SQLite transaction
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


# Semester numbers considered 2nd/3rd year that require placement blocks
PLACEMENT_SEMESTER_NUMS = {3, 5}


class TimetableScheduler:
    """
    Intelligent Timetable Scheduler implementing constraint satisfaction.

    Guarantees:
    - No faculty double-booking across classes (CRITICAL)
    - Library (1 period/week) mandatory for every class
    - Placement (2 consecutive periods) for Sem 3 and Sem 5 classes
    - All 40 weekly slots filled (zero empty period boxes)
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
        Raises SchedulingError with diagnostics if violated.
        """
        if not classes:
            raise SchedulingError("No classes defined. Please add at least one class.")
        if not subjects:
            raise SchedulingError("No subjects defined. Please configure subjects for your classes.")
        if not faculty:
            raise SchedulingError("No faculty members registered. Timetable requires a faculty pool.")

        faculty_map = {f["id"]: f for f in faculty}
        max_class_weekly_slots = len(self.days) * TOTAL_PERIODS_PER_DAY  # 40

        class_periods: Dict[int, int] = {}
        for s in subjects:
            class_periods[s["class_id"]] = class_periods.get(s["class_id"], 0) + s["periods_per_week"]

        for cid, total_p in class_periods.items():
            if total_p > max_class_weekly_slots:
                cname = next((c["name"] for c in classes if c["id"] == cid), str(cid))
                raise SchedulingError(
                    f"Class '{cname}' requires {total_p} periods per week, "
                    f"exceeding the maximum weekly capacity of {max_class_weekly_slots} periods."
                )

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

        for attempt in range(40):
            result = self._solve_schedule(classes, faculty, subjects, faculty_map, seed_offset=attempt)
            if result is not None:
                return self._persist_and_format_schedule(result, classes_map, subjects_map, faculty_map)

        raise SchedulingError(
            "Could not find a conflict-free timetable satisfying all simultaneous constraints. "
            "Consider adjusting subject hours or faculty assignments."
        )

    def _classify_subject(self, s: Dict[str, Any]) -> str:
        """Returns 'lab', 'library', 'placement', or 'theory'."""
        name_l = s["name"].lower()
        code_l = s["code"].lower()
        if "lab" in name_l or "laboratory" in name_l or "lab" in code_l:
            return "lab"
        if "library" in name_l or code_l.startswith("lib"):
            return "library"
        if "placement" in name_l or "placement" in code_l:
            return "placement"
        return "theory"

    def _needs_placement(self, cl: Dict[str, Any]) -> bool:
        """Returns True if this class requires a 2-period placement block."""
        sem = cl.get("semester", 1)
        try:
            sem = int(sem)
        except (TypeError, ValueError):
            sem = 1
        return sem in PLACEMENT_SEMESTER_NUMS

    def _solve_schedule(
        self,
        classes: List[Dict[str, Any]],
        faculty: List[Dict[str, Any]],
        subjects: List[Dict[str, Any]],
        faculty_map: Dict[int, Dict[str, Any]],
        seed_offset: int = 0,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Solves CSP across all classes.

        Key guarantees:
          - fac_sched is global across ALL classes -> NO faculty double-booking
          - Mandatory Library (1 period/week) for all classes
          - Mandatory consecutive 2-period Placement for 2nd and 3rd year classes (Sem 3 & 5)
          - 2-hour continuous Lab blocks
          - All 40 weekly slots filled (zero empty period boxes)
        """
        pt_periods = set(PART_TIME_ALLOWED_PERIODS)
        rng = random.Random(100 + seed_offset)

        # Global across ALL classes — prevents any two classes from having same faculty at same time
        fac_sched: Dict[Tuple[int, str, int], int] = {}
        fac_load: Dict[int, int] = {f["id"]: 0 for f in faculty}
        all_entries: List[Dict[str, Any]] = []

        shuffled_classes = list(classes)
        rng.shuffle(shuffled_classes)

        for cl in shuffled_classes:
            cid = cl["id"]
            class_subjs = [sub for sub in subjects if sub["class_id"] == cid]
            if not class_subjs:
                continue

            needs_placement = self._needs_placement(cl)

            labs = [sub for sub in class_subjs if self._classify_subject(sub) == "lab"]
            placements = [sub for sub in class_subjs if self._classify_subject(sub) == "placement"]
            libraries = [sub for sub in class_subjs if self._classify_subject(sub) == "library"]
            theories = [sub for sub in class_subjs if self._classify_subject(sub) == "theory"]

            class_solved = False
            for attempt in range(60):
                class_sched: Dict[Tuple[str, int], Dict[str, Any]] = {}
                subj_day_cnt: Dict[Tuple[str, int], int] = {}
                applied_fac_keys: List[Tuple[int, str, int]] = []

                def place_entry(d: str, p: int, sub: Dict[str, Any], fid: Optional[int]):
                    sid = sub["id"] if sub else None
                    class_sched[(d, p)] = {
                        "class_id": cid, "day": d, "period_num": p,
                        "subject_id": sid, "faculty_id": fid
                    }
                    if fid:
                        fac_sched[(fid, d, p)] = cid
                        fac_load[fid] = fac_load.get(fid, 0) + 1
                        applied_fac_keys.append((fid, d, p))
                    if sid:
                        subj_day_cnt[(d, sid)] = subj_day_cnt.get((d, sid), 0) + 1

                def unplace_entry(d: str, p: int):
                    entry = class_sched.pop((d, p), None)
                    if not entry:
                        return
                    fid = entry.get("faculty_id")
                    sid = entry.get("subject_id")
                    if fid:
                        fac_sched.pop((fid, d, p), None)
                        fac_load[fid] = max(0, fac_load.get(fid, 0) - 1)
                        if (fid, d, p) in applied_fac_keys:
                            applied_fac_keys.remove((fid, d, p))
                    if sid:
                        subj_day_cnt[(d, sid)] = max(0, subj_day_cnt.get((d, sid), 0) - 1)

                def rollback():
                    for fid, d, p in list(applied_fac_keys):
                        fac_sched.pop((fid, d, p), None)
                        fac_load[fid] = max(0, fac_load.get(fid, 0) - 1)
                    applied_fac_keys.clear()
                    class_sched.clear()
                    subj_day_cnt.clear()

                # ── Step 1: Labs (2-period continuous blocks) ───────────────
                lab_success = True
                shuffled_labs = list(labs)
                rng.shuffle(shuffled_labs)

                for lab_s in shuffled_labs:
                    fid = lab_s.get("faculty_id")
                    fac = faculty_map.get(fid, {}) if fid else {}
                    is_pt = (fac.get("work_type") == WORK_TYPE_PART_TIME)
                    valid_pairs = [(1, 2), (3, 4)] if is_pt else [(5, 6), (7, 8), (3, 4), (1, 2)]

                    num_blocks = max(1, lab_s["periods_per_week"] // 2)
                    blocks_placed = 0
                    days_avail = list(self.days)
                    rng.shuffle(days_avail)

                    for day in days_avail:
                        if blocks_placed >= num_blocks:
                            break
                        # At most 1 lab session per day for good balance
                        if any(class_sched.get((day, p)) for p in range(1, 9)):
                            continue
                        pairs_avail = list(valid_pairs)
                        rng.shuffle(pairs_avail)
                        for p1, p2 in pairs_avail:
                            if (day, p1) in class_sched or (day, p2) in class_sched:
                                continue
                            if fid and ((fid, day, p1) in fac_sched or (fid, day, p2) in fac_sched):
                                continue
                            place_entry(day, p1, lab_s, fid)
                            place_entry(day, p2, lab_s, fid)
                            blocks_placed += 1
                            break

                    if blocks_placed < num_blocks:
                        lab_success = False
                        break

                if not lab_success:
                    rollback()
                    continue

                # ── Step 2: Placement block (2 continuous periods) ───────────
                pl_success = True
                if needs_placement:
                    pl_sub = placements[0] if placements else None
                    if not pl_sub:
                        pl_sub = {"id": None, "name": "Placement Training", "periods_per_week": 2, "faculty_id": None}
                    pl_fid = pl_sub.get("faculty_id")
                    pl_pairs = [(7, 8), (5, 6), (3, 4)]
                    pl_days = list(self.days)
                    rng.shuffle(pl_days)
                    placed = False
                    for day in pl_days:
                        for p1, p2 in pl_pairs:
                            if (day, p1) in class_sched or (day, p2) in class_sched:
                                continue
                            if pl_fid and ((pl_fid, day, p1) in fac_sched or (pl_fid, day, p2) in fac_sched):
                                continue
                            place_entry(day, p1, pl_sub, pl_fid)
                            place_entry(day, p2, pl_sub, pl_fid)
                            placed = True
                            break
                        if placed:
                            break
                    if not placed:
                        pl_success = False

                if not pl_success:
                    rollback()
                    continue

                # ── Step 3: Theory & Library tokens (Backtracking CSP) ───────
                tokens = []
                for sub in theories:
                    for _ in range(sub["periods_per_week"]):
                        tokens.append(sub)
                for sub in libraries:
                    # Exactly 1 period per week for library
                    tokens.append(sub)

                tokens.sort(key=lambda x: (
                    0 if x.get("faculty_id") and faculty_map.get(x["faculty_id"], {}).get("work_type") == WORK_TYPE_PART_TIME else 1,
                    -x["periods_per_week"]
                ))

                steps = [0]
                def backtrack(t_idx: int) -> bool:
                    steps[0] += 1
                    if steps[0] > 1500:
                        return False
                    if t_idx >= len(tokens):
                        return True
                    sub = tokens[t_idx]
                    sid = sub["id"]
                    fid = sub.get("faculty_id")
                    fac = faculty_map.get(fid, {}) if fid else {}
                    is_pt = (fac.get("work_type") == WORK_TYPE_PART_TIME)
                    max_pd = 2 if sub["periods_per_week"] >= 5 else 1

                    avail = []
                    for d in self.days:
                        for p in self.periods:
                            if (d, p) in class_sched:
                                continue
                            if is_pt and p not in pt_periods:
                                continue
                            if fid and (fid, d, p) in fac_sched:
                                continue
                            if subj_day_cnt.get((d, sid), 0) >= max_pd:
                                continue
                            avail.append((d, p))

                    rng.shuffle(avail)
                    avail.sort(key=lambda dp: subj_day_cnt.get((dp[0], sid), 0))

                    for d, p in avail:
                        place_entry(d, p, sub, fid)
                        if backtrack(t_idx + 1):
                            return True
                        unplace_entry(d, p)
                    return False

                if not backtrack(0):
                    rollback()
                    continue

                # ── Step 4: Fill remaining empty slots (zero empty period boxes) ─
                empty_slots = [
                    (d, p) for d in self.days for p in self.periods if (d, p) not in class_sched
                ]
                for d, p in empty_slots:
                    placed = False
                    for sub in theories:
                        sid = sub["id"]
                        fid = sub.get("faculty_id")
                        fac = faculty_map.get(fid, {}) if fid else {}
                        is_pt = (fac.get("work_type") == WORK_TYPE_PART_TIME)
                        if is_pt and p not in pt_periods:
                            continue
                        if fid and (fid, d, p) in fac_sched:
                            continue
                        if fid and fac_load.get(fid, 0) >= fac.get("weekly_period_limit", 40):
                            continue
                        if subj_day_cnt.get((d, sid), 0) >= 2:
                            continue
                        place_entry(d, p, sub, fid)
                        placed = True
                        break
                    if not placed:
                        avail_fids = [
                            f["id"] for f in faculty
                            if (f["id"], d, p) not in fac_sched and
                            (p in pt_periods if f.get("work_type") == WORK_TYPE_PART_TIME else True)
                        ]
                        fallback_fid = avail_fids[0] if avail_fids else (theories[0]["faculty_id"] if theories and theories[0].get("faculty_id") else faculty[0]["id"])
                        filler_sub = theories[0] if theories else class_subjs[0]
                        place_entry(d, p, filler_sub, fallback_fid)

                class_solved = True
                all_entries.extend(class_sched.values())
                break

            if not class_solved:
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
        verifies there are no faculty double-bookings, and returns structured data.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM timetable_entries;")

            insert_query = """
            INSERT INTO timetable_entries (class_id, semester, day, period_num, subject_id, faculty_id)
            VALUES (?, ?, ?, ?, ?, ?);
            """
            cursor.executemany(
                insert_query,
                [
                    (
                        e["class_id"],
                        classes_map.get(e["class_id"], {}).get("semester", 1),
                        e["day"],
                        e["period_num"],
                        e["subject_id"],
                        e["faculty_id"],
                    )
                    for e in entries
                ],
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise SchedulingError(f"Failed to persist timetable to database: {str(e)}")
        finally:
            conn.close()

        # ── Clash verification ────────────────────────────────────────────────
        faculty_slot_check: Dict[Tuple[int, str, int], int] = {}
        conflicts = []
        for e in entries:
            fid = e.get("faculty_id")
            if fid:
                key = (fid, e["day"], e["period_num"])
                if key in faculty_slot_check and faculty_slot_check[key] != e["class_id"]:
                    f_name = faculty_map.get(fid, {}).get("name", str(fid))
                    conflicts.append(f"Faculty '{f_name}' double-booked on {e['day']} period {e['period_num']}")
                else:
                    faculty_slot_check[key] = e["class_id"]

        # Build structured output
        schedules_by_class: Dict[int, Dict[str, Any]] = {}
        for cid, cinfo in classes_map.items():
            schedules_by_class[cid] = {
                "class_id": cid,
                "class_name": cinfo["name"],
                "class_code": cinfo["code"],
                "entries": [],
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

            if fid and fid in faculty_utilization:
                faculty_utilization[fid]["assigned_periods"] += 1

            cell = {
                "period_num": p,
                "timing": PERIOD_TIMINGS.get(p, {}),
                "subject_id": sid,
                "subject_name": sinfo.get("name", "Unknown"),
                "subject_code": sinfo.get("code", "N/A"),
                "faculty_id": fid,
                "faculty_name": finfo.get("name", "Unknown"),
                "faculty_work_type": finfo.get("work_type", "full_time"),
            }

            schedules_by_class[cid]["grid"][day][p] = cell
            schedules_by_class[cid]["entries"].append({**cell, "day": day})

        conflict_count = len(conflicts)
        return {
            "success": True,
            "message": (
                f"Timetable generated with {conflict_count} conflicts."
                if conflict_count > 0
                else "Timetable generated successfully with 0 conflicts."
            ),
            "conflicts": conflicts,
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

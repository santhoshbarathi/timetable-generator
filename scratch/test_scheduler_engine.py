"""
Test scheduling algorithm with 40 periods per class (zero free periods),
lab 2 hours, theory up to 6 periods, library 1 period, placement 2 periods.
"""

import random
import itertools
from typing import Dict, List, Tuple, Optional, Any

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PERIODS = list(range(1, 9))
PT_PERIODS = [1, 2, 3, 4]
FT_PERIODS = list(range(1, 9))

def solve_timetable(classes, faculty, subjects, seed=42):
    rng = random.Random(seed)
    faculty_map = {f["id"]: f for f in faculty}
    
    # Track assignments
    # (class_id, day, period) -> entry
    class_sched = {}
    # (faculty_id, day, period) -> entry
    fac_sched = {}
    # (class_id, day, subject_id) -> count
    subj_day_count = {}
    # faculty_id -> weekly count
    fac_load = {f["id"]: 0 for f in faculty}
    
    # We will schedule class by class or subject by subject
    # Sort subjects: Most constrained first
    # 1. Labs (need 2 consecutive periods)
    # 2. Part-time faculty subjects
    # 3. 6-period theory subjects
    # 4. Other theory subjects
    # 5. Placement & Library
    
    def subject_sort_key(s):
        is_lab = 1 if "lab" in s["name"].lower() or "laboratory" in s["name"].lower() else 0
        fid = s["faculty_id"]
        is_pt = 1 if fid and faculty_map[fid]["work_type"] == "part_time" else 0
        periods = s["periods_per_week"]
        # Prioritize: labs first, then part-time, then high period count
        return (-is_lab, -is_pt, -periods)

    # Let's break each subject into session units:
    # If lab with 2 periods: 1 session of 2 consecutive periods!
    # If 6-period theory: 4 sessions of 1 period + 1 session of 2 periods (or 6 sessions of 1 period)
    # If 5-period theory: 5 sessions of 1 period (distinct days)
    # If placement (2 periods): 2 sessions of 1 period (or 1 session of 2 periods)
    # If library (1 period): 1 session of 1 period
    
    units = []
    for s in sorted(subjects, key=subject_sort_key):
        cid = s["class_id"]
        sid = s["id"]
        k = s["periods_per_week"]
        is_lab = "lab" in s["name"].lower() or "laboratory" in s["name"].lower()
        
        if is_lab and k == 2:
            # 1 block of 2 consecutive periods
            units.append({"subject": s, "type": "block2", "size": 2})
        elif k == 6:
            # Needs 6 periods on 5 days: 1 day gets 2 periods, 4 days get 1 period
            # Or 6 single periods with at most 2 per day
            for _ in range(k):
                units.append({"subject": s, "type": "single", "size": 1})
        else:
            for _ in range(k):
                units.append({"subject": s, "type": "single", "size": 1})

    print(f"Total units to schedule: {len(units)} (Total periods: {sum(u['size'] for u in units)})")
    
    # Backtracking search with randomized restart
    def backtrack(idx):
        if idx >= len(units):
            return True
            
        u = units[idx]
        s = u["subject"]
        cid = s["class_id"]
        sid = s["id"]
        fid = s["faculty_id"]
        fac = faculty_map[fid]
        wtype = fac["work_type"]
        is_pt = (wtype == "part_time")
        
        # Check weekly capacity
        if fac_load[fid] + u["size"] > fac["weekly_period_limit"]:
            return False
            
        allowed_p = PT_PERIODS if is_pt else FT_PERIODS
        
        if u["type"] == "block2":
            # Lab block of 2 consecutive periods on 1 day
            # Valid period pairs: (1,2), (3,4), (5,6), (7,8)
            valid_pairs = [(1,2), (3,4)] if is_pt else [(3,4), (5,6), (7,8), (1,2)]
            
            shuffled_days = list(DAYS)
            rng.shuffle(shuffled_days)
            
            for day in shuffled_days:
                if subj_day_count.get((cid, day, sid), 0) > 0:
                    continue
                shuffled_pairs = list(valid_pairs)
                rng.shuffle(shuffled_pairs)
                for p1, p2 in shuffled_pairs:
                    if (cid, day, p1) in class_sched or (cid, day, p2) in class_sched:
                        continue
                    if (fid, day, p1) in fac_sched or (fid, day, p2) in fac_sched:
                        continue
                        
                    # Apply
                    e1 = {"class_id": cid, "day": day, "period_num": p1, "subject_id": sid, "faculty_id": fid}
                    e2 = {"class_id": cid, "day": day, "period_num": p2, "subject_id": sid, "faculty_id": fid}
                    class_sched[(cid, day, p1)] = e1
                    class_sched[(cid, day, p2)] = e2
                    fac_sched[(fid, day, p1)] = e1
                    fac_sched[(fid, day, p2)] = e2
                    subj_day_count[(cid, day, sid)] = 2
                    fac_load[fid] += 2
                    
                    if backtrack(idx + 1):
                        return True
                        
                    # Rollback
                    class_sched.pop((cid, day, p1), None)
                    class_sched.pop((cid, day, p2), None)
                    fac_sched.pop((fid, day, p1), None)
                    fac_sched.pop((fid, day, p2), None)
                    subj_day_count[(cid, day, sid)] = 0
                    fac_load[fid] -= 2
                    
            return False
            
        else:
            # Single period
            # Order candidate slots: day, period
            # Limit on same day:
            max_per_day = 2 if s["periods_per_week"] >= 6 else 1
            
            # Find eligible (day, period) slots
            candidates = []
            for day in DAYS:
                cur_day_cnt = subj_day_count.get((cid, day, sid), 0)
                if cur_day_cnt >= max_per_day:
                    continue
                for p in allowed_p:
                    if (cid, day, p) in class_sched:
                        continue
                    if (fid, day, p) in fac_sched:
                        continue
                    candidates.append((day, p))
                    
            # Shuffle candidates to balance
            rng.shuffle(candidates)
            # Heuristic: sort candidates so days with 0 of this subject come before days with 1
            candidates.sort(key=lambda dp: subj_day_count.get((cid, dp[0], sid), 0))
            
            for day, p in candidates:
                entry = {"class_id": cid, "day": day, "period_num": p, "subject_id": sid, "faculty_id": fid}
                class_sched[(cid, day, p)] = entry
                fac_sched[(fid, day, p)] = entry
                subj_day_count[(cid, day, sid)] = subj_day_count.get((cid, day, sid), 0) + 1
                fac_load[fid] += 1
                
                if backtrack(idx + 1):
                    return True
                    
                class_sched.pop((cid, day, p), None)
                fac_sched.pop((fid, day, p), None)
                subj_day_count[(cid, day, sid)] -= 1
                fac_load[fid] -= 1
                
            return False

    for attempt in range(20):
        print(f"Solving attempt {attempt + 1}...")
        class_sched.clear()
        fac_sched.clear()
        subj_day_count.clear()
        for f in faculty:
            fac_load[f["id"]] = 0
        rng = random.Random(100 + attempt * 7)
        rng.shuffle(units)
        # Keep block2 units at the start of their class
        units.sort(key=lambda u: 0 if u["type"] == "block2" else (1 if faculty_map[u["subject"]["faculty_id"]]["work_type"] == "part_time" else 2))
        
        if backtrack(0):
            print("Successfully found schedule!")
            return list(class_sched.values())
            
    print("Failed to find schedule in 20 attempts")
    return None

if __name__ == "__main__":
    print("Engine module ready.")

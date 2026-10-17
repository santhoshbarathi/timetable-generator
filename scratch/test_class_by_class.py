"""
Class-by-Class CSP Scheduler Engine.
Solves each class sequentially while respecting shared faculty constraints.
Runs in milliseconds!
"""

import random
from typing import Dict, List, Tuple, Optional, Any

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PT_PERIODS = [1, 2, 3, 4]
FT_PERIODS = list(range(1, 9))

def solve_class_by_class(classes, faculty, subjects, seed=42):
    rng = random.Random(seed)
    faculty_map = {f["id"]: f for f in faculty}
    
    # Global state tracking across classes
    # (faculty_id, day, period) -> entry
    fac_sched = {}
    # faculty_id -> weekly load
    fac_load = {f["id"]: 0 for f in faculty}
    # all scheduled entries
    all_entries = []

    # Order classes: classes sharing more faculty or with part-time faculty first
    for cl in classes:
        cid = cl["id"]
        class_subjects = [s for s in subjects if s["class_id"] == cid]
        
        # Prepare session units for this class
        # Labs (2 consecutive hours)
        lab_units = []
        theory_units = []
        
        for s in class_subjects:
            k = s["periods_per_week"]
            is_lab = "lab" in s["name"].lower() or "laboratory" in s["name"].lower()
            if is_lab and k == 2:
                lab_units.append(s)
            elif k == 6:
                for _ in range(6):
                    theory_units.append(s)
            else:
                for _ in range(k):
                    theory_units.append(s)
                    
        total_p = sum(s["periods_per_week"] for s in class_subjects)
        # print(f"Scheduling class {cl['code']}: {len(lab_units)} labs, {len(theory_units)} theory units (Total {total_p} periods)")
        
        # Attempt solving this class with local backtracking
        class_solved = False
        
        for attempt in range(50):
            class_sched = {} # (day, period) -> entry
            subj_day_cnt = {} # (day, subject_id) -> count
            applied_fac_slots = [] # (fid, day, p)
            
            # 1. Place lab units first (each lab takes 2 consecutive periods on 1 day)
            # Valid pairs: (1,2), (3,4), (5,6), (7,8)
            lab_success = True
            shuffled_days = list(DAYS)
            rng.shuffle(shuffled_days)
            
            day_idx = 0
            for lab_s in lab_units:
                fid = lab_s["faculty_id"]
                fac = faculty_map[fid]
                valid_pairs = [(1,2), (3,4)] if fac["work_type"] == "part_time" else [(5,6), (7,8), (3,4), (1,2)]
                
                placed = False
                for _ in range(len(DAYS)):
                    day = shuffled_days[day_idx % len(DAYS)]
                    day_idx += 1
                    
                    rng.shuffle(valid_pairs)
                    for p1, p2 in valid_pairs:
                        if (day, p1) in class_sched or (day, p2) in class_sched:
                            continue
                        if (fid, day, p1) in fac_sched or (fid, day, p2) in fac_sched:
                            continue
                        if fac_load[fid] + 2 > fac["weekly_period_limit"]:
                            continue
                            
                        # Assign lab
                        e1 = {"class_id": cid, "day": day, "period_num": p1, "subject_id": lab_s["id"], "faculty_id": fid}
                        e2 = {"class_id": cid, "day": day, "period_num": p2, "subject_id": lab_s["id"], "faculty_id": fid}
                        class_sched[(day, p1)] = e1
                        class_sched[(day, p2)] = e2
                        applied_fac_slots.append((fid, day, p1, e1))
                        applied_fac_slots.append((fid, day, p2, e2))
                        subj_day_cnt[(day, lab_s["id"])] = 2
                        fac_sched[(fid, day, p1)] = e1
                        fac_sched[(fid, day, p2)] = e2
                        fac_load[fid] += 2
                        placed = True
                        break
                    if placed:
                        break
                        
                if not placed:
                    lab_success = False
                    break
                    
            if not lab_success:
                # Rollback and retry
                for fid, day, p, _ in applied_fac_slots:
                    fac_sched.pop((fid, day, p), None)
                    fac_load[fid] -= 1
                continue
                
            # 2. Backtrack theory units
            # Sort theory units: part-time faculty first, then subjects with 6 periods
            def t_sort(s):
                is_pt = 1 if faculty_map[s["faculty_id"]]["work_type"] == "part_time" else 0
                return (-is_pt, -s["periods_per_week"])
                
            shuffled_theory = sorted(theory_units, key=t_sort)
            
            def backtrack_theory(u_idx):
                if u_idx >= len(shuffled_theory):
                    return True
                s = shuffled_theory[u_idx]
                fid = s["faculty_id"]
                fac = faculty_map[fid]
                is_pt = (fac["work_type"] == "part_time")
                allowed_p = PT_PERIODS if is_pt else FT_PERIODS
                max_per_day = 2 if s["periods_per_week"] >= 6 else 1
                
                # Check weekly faculty capacity
                if fac_load[fid] >= fac["weekly_period_limit"]:
                    return False
                    
                # Collect candidate (day, p)
                candidates = []
                for day in DAYS:
                    if subj_day_cnt.get((day, s["id"]), 0) >= max_per_day:
                        continue
                    for p in allowed_p:
                        if (day, p) in class_sched:
                            continue
                        if (fid, day, p) in fac_sched:
                            continue
                        candidates.append((day, p))
                        
                rng.shuffle(candidates)
                # Sort: days with 0 periods of this subject first
                candidates.sort(key=lambda dp: subj_day_cnt.get((dp[0], s["id"]), 0))
                
                for day, p in candidates:
                    e = {"class_id": cid, "day": day, "period_num": p, "subject_id": s["id"], "faculty_id": fid}
                    class_sched[(day, p)] = e
                    fac_sched[(fid, day, p)] = e
                    subj_day_cnt[(day, s["id"])] = subj_day_cnt.get((day, s["id"]), 0) + 1
                    fac_load[fid] += 1
                    
                    if backtrack_theory(u_idx + 1):
                        return True
                        
                    class_sched.pop((day, p), None)
                    fac_sched.pop((fid, day, p), None)
                    subj_day_cnt[(day, s["id"])] -= 1
                    fac_load[fid] -= 1
                    
                return False

            if backtrack_theory(0):
                # Class successfully scheduled!
                class_solved = True
                all_entries.extend(class_sched.values())
                # print(f"  Class {cl['code']} solved on attempt {attempt + 1}")
                break
            else:
                # Rollback lab units for this attempt
                for fid, day, p, _ in applied_fac_slots:
                    fac_sched.pop((fid, day, p), None)
                    fac_load[fid] -= 1

        if not class_solved:
            print(f"FAILED to solve class {cl['code']}")
            return None

    return all_entries

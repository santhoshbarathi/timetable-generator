"""
Subject-Level Fast CSP Solver with proper Heuristic & Period Search.
"""

import sys
sys.path.insert(0, '.')
import random
import itertools
from collections import Counter
from typing import Dict, List, Tuple, Optional, Any

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PERIODS = list(range(1, 9))
PT_PERIODS = [1, 2, 3, 4]
FT_PERIODS = [5, 6, 7, 8, 4, 3, 2, 1]  # Prefer afternoon for FT to keep morning for PT

def solve_subject_level(classes, faculty, subjects, seed=42):
    rng = random.Random(seed)
    faculty_map = {f["id"]: f for f in faculty}
    
    # Global tracking structures across classes
    class_sched = {}
    fac_sched = {}
    subj_day_cnt = {}
    fac_load = {f["id"]: 0 for f in faculty}
    
    # We solve class-by-class
    for cl in classes:
        cid = cl["id"]
        class_subjects = [s for s in subjects if s["class_id"] == cid]
        
        # Sort subjects: Most Constrained Variable (MCV) First:
        # 1. Part-time faculty (CRITICAL: can ONLY take periods 1-4, so must be scheduled FIRST!)
        # 2. Labs (2 consecutive hours)
        # 3. 6-period theory subjects
        # 4. Other theory subjects
        # 5. Placement & Library
        def s_key(s):
            fid = s["faculty_id"]
            is_pt = 1 if fid and faculty_map[fid]["work_type"] == "part_time" else 0
            is_lab = 1 if "lab" in s["name"].lower() or "laboratory" in s["name"].lower() else 0
            return (-is_pt, -is_lab, -s["periods_per_week"])
            
        sorted_subjs = sorted(class_subjects, key=s_key)
        
        class_solved = False
        for attempt in range(100):
            local_entries = []
            
            def backtrack(s_idx):
                if s_idx >= len(sorted_subjs):
                    return True
                    
                s = sorted_subjs[s_idx]
                sid = s["id"]
                fid = s["faculty_id"]
                fac = faculty_map[fid]
                is_pt = (fac["work_type"] == "part_time")
                k = s["periods_per_week"]
                is_lab = ("lab" in s["name"].lower() or "laboratory" in s["name"].lower()) and k == 2
                
                if fac_load[fid] + k > fac["weekly_period_limit"]:
                    return False
                    
                allowed_p = list(PT_PERIODS) if is_pt else list(FT_PERIODS)
                
                if is_lab:
                    # Lab: 2 consecutive periods on 1 day
                    lab_pairs = [(1,2), (3,4)] if is_pt else [(5,6), (7,8), (3,4), (1,2)]
                    shuffled_days = list(DAYS)
                    rng.shuffle(shuffled_days)
                    
                    for day in shuffled_days:
                        if subj_day_cnt.get((cid, day, sid), 0) > 0:
                            continue
                        shuffled_pairs = list(lab_pairs)
                        rng.shuffle(shuffled_pairs)
                        for p1, p2 in shuffled_pairs:
                            if (cid, day, p1) in class_sched or (cid, day, p2) in class_sched:
                                continue
                            if (fid, day, p1) in fac_sched or (fid, day, p2) in fac_sched:
                                continue
                                
                            e1 = {"class_id": cid, "day": day, "period_num": p1, "subject_id": sid, "faculty_id": fid}
                            e2 = {"class_id": cid, "day": day, "period_num": p2, "subject_id": sid, "faculty_id": fid}
                            class_sched[(cid, day, p1)] = e1
                            class_sched[(cid, day, p2)] = e2
                            fac_sched[(fid, day, p1)] = e1
                            fac_sched[(fid, day, p2)] = e2
                            subj_day_cnt[(cid, day, sid)] = 2
                            fac_load[fid] += 2
                            local_entries.extend([e1, e2])
                            
                            if backtrack(s_idx + 1):
                                return True
                                
                            class_sched.pop((cid, day, p1), None)
                            class_sched.pop((cid, day, p2), None)
                            fac_sched.pop((fid, day, p1), None)
                            fac_sched.pop((fid, day, p2), None)
                            subj_day_cnt[(cid, day, sid)] = 0
                            fac_load[fid] -= 2
                            local_entries.pop()
                            local_entries.pop()
                    return False
                    
                elif k == 6:
                    day_combos = []
                    for extra_day in DAYS:
                        day_combos.append(list(DAYS) + [extra_day])
                    rng.shuffle(day_combos)
                    
                    for day_list in day_combos:
                        day_counts = Counter(day_list)
                        possible = True
                        chosen_day_periods = {}
                        
                        for d, needed_cnt in day_counts.items():
                            avail = [p for p in allowed_p if (cid, d, p) not in class_sched and (fid, d, p) not in fac_sched]
                            if len(avail) < needed_cnt:
                                possible = False
                                break
                            # For FT, prefer afternoon slots first
                            chosen_day_periods[d] = avail[:needed_cnt]
                            
                        if not possible:
                            continue
                            
                        applied = []
                        for d, plist in chosen_day_periods.items():
                            for p in plist:
                                e = {"class_id": cid, "day": d, "period_num": p, "subject_id": sid, "faculty_id": fid}
                                class_sched[(cid, d, p)] = e
                                fac_sched[(fid, d, p)] = e
                                subj_day_cnt[(cid, d, sid)] = subj_day_cnt.get((cid, d, sid), 0) + 1
                                fac_load[fid] += 1
                                applied.append(e)
                                local_entries.append(e)
                                
                        if backtrack(s_idx + 1):
                            return True
                            
                        for e in applied:
                            class_sched.pop((cid, e["day"], e["period_num"]), None)
                            fac_sched.pop((fid, e["day"], e["period_num"]), None)
                            subj_day_cnt[(cid, e["day"], sid)] -= 1
                            fac_load[fid] -= 1
                            local_entries.remove(e)
                    return False
                    
                else:
                    combos = list(itertools.combinations(DAYS, k))
                    rng.shuffle(combos)
                    
                    for day_tuple in combos:
                        possible = True
                        chosen_slots = []
                        for d in day_tuple:
                            avail = [p for p in allowed_p if (cid, d, p) not in class_sched and (fid, d, p) not in fac_sched]
                            if not avail:
                                possible = False
                                break
                            chosen_slots.append((d, avail[0]))
                            
                        if not possible:
                            continue
                            
                        applied = []
                        for d, p in chosen_slots:
                            e = {"class_id": cid, "day": d, "period_num": p, "subject_id": sid, "faculty_id": fid}
                            class_sched[(cid, d, p)] = e
                            fac_sched[(fid, d, p)] = e
                            subj_day_cnt[(cid, d, sid)] = subj_day_cnt.get((cid, d, sid), 0) + 1
                            fac_load[fid] += 1
                            applied.append(e)
                            local_entries.append(e)
                            
                        if backtrack(s_idx + 1):
                            return True
                            
                        for e in applied:
                            class_sched.pop((cid, e["day"], e["period_num"]), None)
                            fac_sched.pop((fid, e["day"], e["period_num"]), None)
                            subj_day_cnt[(cid, e["day"], sid)] -= 1
                            fac_load[fid] -= 1
                            local_entries.remove(e)
                    return False

            if backtrack(0):
                class_solved = True
                break
                
        if not class_solved:
            print(f"Failed to solve class {cl['code']}")
            return None

    return list(class_sched.values())

if __name__ == "__main__":
    from scratch.populate_40_periods_test import classes, faculty, subjects
    res = solve_subject_level(classes, faculty, subjects)
    if res:
        print(f"SUCCESS: Scheduled {len(res)} periods across {len(classes)} classes!")
        cnts = Counter(e["class_id"] for e in res)
        for c in classes:
            print(f"  Class {c['code']}: {cnts[c['id']]}/40 periods")
    else:
        print("FAILED")

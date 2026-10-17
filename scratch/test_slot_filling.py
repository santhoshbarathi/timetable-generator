"""
Slot-Filling CSP Solver for 40 periods per class.
Directly fills the 40 slots per class with subjects.
"""

import sys
sys.path.insert(0, '.')
import random
from collections import Counter
from scratch.populate_40_periods_test import classes, faculty, subjects

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PERIODS = list(range(1, 9))
PT_PERIODS = {1, 2, 3, 4}

def solve_all(classes, faculty, subjects, seed=42):
    rng = random.Random(seed)
    faculty_map = {f["id"]: f for f in faculty}
    
    # Global state across classes
    # (faculty_id, day, period) -> entry
    fac_sched = {}
    fac_load = {f["id"]: 0 for f in faculty}
    all_entries = []
    
    # Lab pairs
    LAB_PAIRS = [(1, 2), (3, 4), (5, 6), (7, 8)]

    for cl in classes:
        cid = cl["id"]
        class_subjs = [s for s in subjects if s["class_id"] == cid]
        
        # Split subjects into Labs and Non-Labs
        labs = [s for s in class_subjs if ("lab" in s["name"].lower() or "laboratory" in s["name"].lower()) and s["periods_per_week"] == 2]
        non_labs = [s for s in class_subjs if s not in labs]
        
        # Flatten non-labs into individual period tokens
        tokens = []
        for s in non_labs:
            for _ in range(s["periods_per_week"]):
                tokens.append(s)
                
        # Total periods
        total_p = sum(s["periods_per_week"] for s in class_subjs)
        assert total_p == 40, f"Class {cl['code']} total periods is {total_p}, expected 40!"
        
        # Sort tokens: Part-time first!
        def token_key(s):
            is_pt = 1 if faculty_map[s["faculty_id"]]["work_type"] == "part_time" else 0
            return (-is_pt, -s["periods_per_week"])
            
        tokens.sort(key=token_key)
        
        # Local class solver
        solved = False
        for attempt in range(100):
            class_sched = {} # (day, p) -> entry
            subj_day_cnt = {} # (day, sid) -> count
            applied_fac = [] # (fid, day, p, entry)
            
            # Step 1: Schedule labs (each lab takes a 2-hour block)
            lab_success = True
            shuffled_days = list(DAYS)
            rng.shuffle(shuffled_days)
            
            for i, lab_s in enumerate(labs):
                fid = lab_s["faculty_id"]
                fac = faculty_map[fid]
                is_pt = (fac["work_type"] == "part_time")
                valid_pairs = [(1,2), (3,4)] if is_pt else [(5,6), (7,8), (3,4), (1,2)]
                
                day = shuffled_days[i % len(DAYS)]
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
            empty_slots = [(d, p) for d in DAYS for p in PERIODS if (d, p) not in class_sched]
            assert len(empty_slots) == len(tokens), f"Mismatch: {len(empty_slots)} empty slots vs {len(tokens)} tokens"
            
            def backtrack_tokens(t_idx):
                if t_idx >= len(tokens):
                    return True
                s = tokens[t_idx]
                sid = s["id"]
                fid = s["faculty_id"]
                fac = faculty_map[fid]
                is_pt = (fac["work_type"] == "part_time")
                max_per_day = 2 if s["periods_per_week"] >= 5 else 1
                
                if fac_load[fid] >= fac["weekly_period_limit"]:
                    return False
                    
                # Find available empty slots
                avail_slots = []
                for d, p in empty_slots:
                    if (d, p) in class_sched:
                        continue
                    if is_pt and p not in PT_PERIODS:
                        continue
                    if (fid, d, p) in fac_sched:
                        continue
                    if subj_day_cnt.get((d, sid), 0) >= max_per_day:
                        continue
                    avail_slots.append((d, p))
                    
                rng.shuffle(avail_slots)
                # Sort heuristic: prefer days where this subject has 0 periods
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
                # print(f"  Class {cl['code']} successfully scheduled!")
                break
            else:
                for fid, day, p, _ in applied_fac:
                    fac_sched.pop((fid, day, p), None)
                    fac_load[fid] -= 1

        if not solved:
            print(f"FAILED for class {cl['code']}")
            return None

    return all_entries

if __name__ == "__main__":
    res = solve_all(classes, faculty, subjects)
    if res:
        print(f"SUCCESS! Total scheduled entries: {len(res)} / 280 (Zero free periods)")
        cnts = Counter(e["class_id"] for e in res)
        for c in classes:
            print(f"  {c['code']}: {cnts[c['id']]}/40 periods")
    else:
        print("FAILED")

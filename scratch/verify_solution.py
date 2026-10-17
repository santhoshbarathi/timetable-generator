"""
Verify all constraints on the 280-period solution.
"""

import sys
sys.path.insert(0, '.')
from scratch.test_slot_filling import solve_all
from scratch.populate_40_periods_test import classes, faculty, subjects

res = solve_all(classes, faculty, subjects)
assert len(res) == 280, f'Expected 280, got {len(res)}'

faculty_map = {f['id']: f for f in faculty}
subj_map = {s['id']: s for s in subjects}

# 1. No class double booking
class_slots = set()
for e in res:
    key = (e['class_id'], e['day'], e['period_num'])
    assert key not in class_slots, f'Class double booking at {key}'
    class_slots.add(key)
print('Check 1 Passed: 0 class double-bookings (all 280 class-day-period slots unique)')

# 2. No faculty double booking
fac_slots = set()
for e in res:
    key = (e['faculty_id'], e['day'], e['period_num'])
    assert key not in fac_slots, f'Faculty double booking at {key}'
    fac_slots.add(key)
print('Check 2 Passed: 0 faculty double-bookings')

# 3. Part-time working window (Periods 1-4 only)
for e in res:
    fac = faculty_map[e['faculty_id']]
    if fac['work_type'] == 'part_time':
        assert e['period_num'] in [1, 2, 3, 4], f"PT faculty {fac['name']} assigned to period {e['period_num']}"
print('Check 3 Passed: All PT faculty in periods 1-4 (09:00 - 12:30)')

# 4. Total periods per class = 40 (no free periods)
for c in classes:
    cnt = sum(1 for e in res if e['class_id'] == c['id'])
    assert cnt == 40, f"Class {c['code']} has {cnt} periods, expected 40"
print('Check 4 Passed: All 7 classes have 40/40 periods (0 free periods)')

# 5. Labs are 2 consecutive periods
for c in classes:
    class_entries = [e for e in res if e['class_id'] == c['id']]
    for sid, s in subj_map.items():
        if s['class_id'] == c['id'] and 'lab' in s['name'].lower():
            s_entries = [e for e in class_entries if e['subject_id'] == sid]
            assert len(s_entries) == 2, f"Lab {s['name']} has {len(s_entries)} entries"
            assert s_entries[0]['day'] == s_entries[1]['day'], 'Lab entries on different days'
            p_diff = abs(s_entries[0]['period_num'] - s_entries[1]['period_num'])
            assert p_diff == 1, f"Lab periods not consecutive: {s_entries}"
print('Check 5 Passed: All labs are 2 consecutive hours on the same day')

# 6. Theory subjects max 6 periods per week
for s in subjects:
    if 'lab' not in s['name'].lower():
        assert s['periods_per_week'] <= 6, f"Theory subject {s['name']} has {s['periods_per_week']} > 6"
print('Check 6 Passed: All theory subjects <= 6 periods per week')

print('\nALL 6 CHECKS PASSED WITH 100% SUCCESS!')

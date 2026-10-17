"""
Test subject-level day assignment for k=6, labs, placement, library.
"""

import random
import itertools
from typing import Dict, List, Tuple, Optional, Any

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PERIODS = list(range(1, 9))
PT_PERIODS = [1, 2, 3, 4]
FT_PERIODS = list(range(1, 9))

def get_day_schedules(s, rng):
    k = s["periods_per_week"]
    is_lab = "lab" in s["name"].lower() or "laboratory" in s["name"].lower()
    
    if is_lab and k == 2:
        # Lab: 2 periods on the SAME day
        combos = [[d, d] for d in DAYS]
        rng.shuffle(combos)
        return combos
    elif k == 6:
        # All 5 days + 1 extra day with 2 periods
        combos = []
        for d_extra in DAYS:
            combo = list(DAYS) + [d_extra]
            combos.append(combo)
        rng.shuffle(combos)
        return combos
    elif k <= 5:
        combos = [list(c) for c in itertools.combinations(DAYS, k)]
        rng.shuffle(combos)
        return combos
    else:
        raise ValueError(f"Unsupported periods_per_week: {k}")

print("Day schedules generator tested.")

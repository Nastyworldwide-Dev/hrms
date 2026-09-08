"""Known RED: one calendar day must retain each contributing shift's pricing.

Run with system Python from the OT worktree. Synthetic DB/calendar boundaries;
actual pairing, interval calculation, day aggregation and public breakdown.
This is an audit reproducer, outside the collected passing regression suite.
"""
import sys
from datetime import datetime, time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hrms/tests"))
from test_ot_nonworking_hours import DAY, TestNonworkingHours, ot, punch

rows = [punch(DAY, value, kind) for value, kind in [("09:00", "IN"), ("12:00", "OUT"), ("13:00", "IN"), ("14:00", "OUT")]]
for row in rows[:2]:
    row.update(shift="SHIFT-NORMAL-SYNTHETIC", shift_start=datetime.combine(DAY, time(9)), shift_end=datetime.combine(DAY, time(11)))
for row in rows[2:]:
    row.update(shift="SHIFT-REST-SYNTHETIC", shift_start=datetime.combine(DAY, time(13)), shift_end=datetime.combine(DAY, time(14)))
fixture = TestNonworkingHours()
with fixture.context(rows=rows, cap=0):
    base = ot._get_shift_ot_config("SHIFT-NORMAL-SYNTHETIC")
    configs = {
        "SHIFT-NORMAL-SYNTHETIC": {**base, "start_time": time(9), "end_time": time(11)},
        "SHIFT-REST-SYNTHETIC": {**base, "start_time": time(13), "end_time": time(14)},
    }
    with patch.object(ot, "_get_shift_ot_config", side_effect=configs.get), patch.object(
        ot, "_classify_day", side_effect=lambda employee, day, default, shift=None: "rest" if shift == "SHIFT-REST-SYNTHETIC" else "normal"
    ):
        result = ot.get_day_ot_breakdown("EMP-SYNTHETIC", DAY)
        print({"actual_hours": result["ot_hours"], "actual_weighted": result["rate_weighted_hours"], "expected_hours": 2, "expected_weighted": 3.5})
        assert result["ot_hours"] == 2
        assert result["rate_weighted_hours"] == 3.5, "OT-MULTI: last shift reprices the earlier shift's contribution"

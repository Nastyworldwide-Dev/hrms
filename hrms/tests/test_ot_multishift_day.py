"""A day worked across two shifts keeps each shift's calendar and rates.

Known red (Astra's OT-MULTI probe, docs/glass/audit/2026-09-08-ot-multishift-
probe.py): one hour of overtime on a normal-day shift at 1.5x followed by one
hour on a rest-day shift at 2x was priced as 4 rate-weighted hours instead of
3.5. The per-day map kept one shift per calendar day — the last one written —
so the earlier shift's hour was re-classified and re-priced by the later
shift. The same collapse let a mixed day's weekday hours escape the weekday
cap (the whole day read as holiday work) and let payroll pay the earlier hour
at the later shift's rate.

Contributions are now kept per (day, shift): each is classified with its own
shift's calendar, qualified against its own minimum, capped by its own daily
and the running monthly cap when it is weekday work, and priced by its own
bands. The public day shape is unchanged for single-shift days.

Bench-free; synthetic punches and per-shift configs. Reuses the shared OT
fixture so persistence, calendar and config boundaries are the same ones
every other OT suite uses.
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_ot_multishift_day.py
"""

import sys
import unittest
from datetime import datetime, time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_ot_nonworking_hours as shared  # module import: its TestCase must not be re-collected here

DAY = shared.DAY
ot = shared.ot
punch = shared.punch

EMPLOYEE = "EMP-SYNTHETIC"
NORMAL = "SHIFT-NORMAL-SYNTHETIC"
REST = "SHIFT-REST-SYNTHETIC"


def _rows(normal=("09:00", "12:00"), rest=("13:00", "14:00")):
	"""A 09-11 normal-day shift followed by a 13-14 rest-day shift on one date."""
	rows = [
		punch(DAY, normal[0], "IN"),
		punch(DAY, normal[1], "OUT"),
		punch(DAY, rest[0], "IN"),
		punch(DAY, rest[1], "OUT"),
	]
	for row in rows[:2]:
		row.update(
			shift=NORMAL,
			shift_start=datetime.combine(DAY, time(9)),
			shift_end=datetime.combine(DAY, time(11)),
		)
	for row in rows[2:]:
		row.update(
			shift=REST,
			shift_start=datetime.combine(DAY, time(13)),
			shift_end=datetime.combine(DAY, time(14)),
		)
	return rows


class _MixedDay:
	"""The shared fixture plus one config per shift and a per-shift calendar."""

	def __init__(self, rows, **context):
		self.fixture = shared.TestNonworkingHours()
		self.rows = rows
		self.context = context

	def __enter__(self):
		self.stack = self.fixture.context(rows=self.rows, **self.context)
		self.stack.__enter__()
		base = ot._get_shift_ot_config(NORMAL)
		configs = {
			NORMAL: {**base, "start_time": time(9), "end_time": time(11)},
			REST: {**base, "start_time": time(13), "end_time": time(14)},
		}
		self.patches = [
			patch.object(ot, "_get_shift_ot_config", side_effect=configs.get),
			patch.object(
				ot,
				"_classify_day",
				side_effect=lambda employee, day, default, shift=None: "rest" if shift == REST else "normal",
			),
		]
		for p in self.patches:
			p.start()
		return self

	def __exit__(self, *exc):
		for p in reversed(self.patches):
			p.stop()
		return self.stack.__exit__(*exc)


class TestMultiShiftDayBreakdown(unittest.TestCase):
	def test_each_shift_keeps_its_own_rate(self):
		with _MixedDay(_rows(), cap=0):
			result = ot.get_day_ot_breakdown(EMPLOYEE, DAY)
		self.assertEqual(result["ot_hours"], 2)
		self.assertEqual(result["rate_weighted_hours"], 3.5)
		self.assertEqual(
			[(band["day_type"], band["rate"], band["hours"]) for band in result["bands"]],
			[("normal", 1.5, 1.0), ("rest", 2, 1.0)],
		)

	def test_weekday_hours_of_a_mixed_day_still_qualify_against_their_own_minimum(self):
		# 09:00-11:20 on the 09-11 shift is 20 min of weekday OT: below the 60-min
		# minimum it earns nothing; the rest-day hour is unaffected by that rule.
		with _MixedDay(_rows(normal=("09:00", "11:20")), cap=0):
			result = ot.get_day_ot_breakdown(EMPLOYEE, DAY)
		self.assertEqual(result["ot_hours"], 1)
		self.assertEqual([band["day_type"] for band in result["bands"]], ["rest"])

	def test_per_day_map_still_totals_the_day(self):
		with _MixedDay(_rows(), cap=0):
			per_day_hours, per_day_shift = ot._per_day_ot_hours(EMPLOYEE, DAY, DAY)
		self.assertEqual(per_day_hours[DAY], 2)
		self.assertIn(per_day_shift[DAY], (NORMAL, REST))


class TestMixedDayClaimCapacity(unittest.TestCase):
	def test_only_the_weekday_part_is_capped(self):
		# 1.5 h weekday OT under a 1 h cap -> 1 h; the rest-day hour is uncapped.
		with _MixedDay(_rows(normal=("09:00", "12:30")), cap=1):
			capacity = ot.get_ot_claim_capacity(EMPLOYEE, DAY, "Overtime Pay")
		self.assertEqual(capacity["hours"], 2.0)
		self.assertEqual(capacity["uncapped_hours"], 1.0)
		self.assertEqual(capacity["monthly_remaining"], 1.0)


class TestMixedDayPayroll(unittest.TestCase):
	def test_approved_hours_are_priced_per_shift_in_work_order(self):
		# basic 2080 / (26 * 8) = 10 per hour: 1 h @1.5 + 1 h @2 = 35, not 2 h @2 = 40.
		with _MixedDay(_rows(), cap=0, approved=((DAY, 2),)):
			amount = ot.get_ot_pay(EMPLOYEE, DAY, DAY, 2080)
		self.assertEqual(amount, 35.0)


if __name__ == "__main__":
	unittest.main()


def _priced_day(contributions, configs, classify):
	"""Run the real day iterator over explicit per-shift contributions."""
	with (
		patch.object(ot, "_per_day_contributions", return_value={DAY: contributions}),
		patch.object(ot, "_get_shift_ot_config", side_effect=configs.get),
		patch.object(ot, "_classify_day", side_effect=classify),
	):
		return list(ot._iter_day_ot(EMPLOYEE, DAY, DAY, 2080, "normal"))


def _config(**overrides):
	base = {
		"min_minutes": 0,
		"days_per_month": 26,
		"hours_per_day": 8,
		"bands": {"normal": [(0, 24, 1.5)], "rest": [(0, 24, 2)]},
		"daily_cap": 0.0,
		"monthly_cap": 0.0,
		"start_time": time(9),
		"end_time": time(18),
		"allow_check_out_after": 0,
	}
	base.update(overrides)
	return base


class TestMixedDayCapsAndApprovals(unittest.TestCase):
	"""Review of db22e3dc3: allowances and caps must survive a day's second shift."""

	def test_approved_hours_trimmed_by_one_shifts_cap_roll_over_to_the_next(self):
		# A raw 2 h under a 1 h daily cap, B raw 3 h under a 5 h cap, 3 h approved:
		# 1 h from A and 2 h from B, not 2 h total with 1 h of approval lost on A.
		rows = _priced_day(
			[{"shift": "A", "hours": 2.0}, {"shift": "B", "hours": 3.0}],
			{"A": _config(daily_cap=1.0), "B": _config(daily_cap=5.0)},
			lambda *a, **k: "normal",
		)
		with (
			patch.object(
				ot,
				"_per_day_contributions",
				return_value={DAY: [{"shift": "A", "hours": 2.0}, {"shift": "B", "hours": 3.0}]},
			),
			patch.object(
				ot,
				"_get_shift_ot_config",
				side_effect={"A": _config(daily_cap=1.0), "B": _config(daily_cap=5.0)}.get,
			),
			patch.object(ot, "_classify_day", return_value="normal"),
		):
			approved = list(ot._iter_day_ot(EMPLOYEE, DAY, DAY, 2080, "normal", {DAY: 3.0}))
		self.assertEqual(rows[0]["normal_hours"], 4.0)  # 1 h (capped) + 3 h, no approval
		self.assertEqual(approved[0]["normal_hours"], 3.0)
		self.assertEqual(approved[0]["amount"], 45.0)  # 3 h x 10/h x 1.5

	def test_the_day_reports_its_tightest_weekday_cap(self):
		# The capacity replay bounds future headroom by this figure: a loose
		# shift on the same day must not hide the tight one.
		rows = _priced_day(
			[{"shift": "TIGHT", "hours": 2.0}, {"shift": "LOOSE", "hours": 1.0}],
			{"TIGHT": _config(monthly_cap=3.0), "LOOSE": _config(monthly_cap=100.0)},
			lambda *a, **k: "normal",
		)
		self.assertEqual(rows[0]["monthly_cap"], 3.0)

	def test_a_shift_resumed_after_another_still_meets_its_own_daily_cap(self):
		# A 1.5 h -> B 0.5 h -> A 1.5 h with A capped at 2 h a day: A is one 3 h
		# contribution capped to 2 h, not two 1.5 h pieces that each pass.
		rows = _priced_day(
			[{"shift": "A", "hours": 1.5}, {"shift": "B", "hours": 0.5}, {"shift": "A", "hours": 1.5}],
			{"A": _config(daily_cap=2.0), "B": _config()},
			lambda *a, **k: "normal",
		)
		by_shift = {}
		for entry in rows[0]["contributions"]:
			by_shift[entry["shift"]] = by_shift.get(entry["shift"], 0) + entry["hours"]
		self.assertEqual(by_shift["A"], 2.0)
		self.assertEqual(by_shift["B"], 0.5)

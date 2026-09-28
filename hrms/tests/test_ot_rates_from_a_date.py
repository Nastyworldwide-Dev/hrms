"""OT rates change on a date and never reprice the days before it.

Owner ruling, 28 Sep 2026 (HR policy changed): Public Holiday pays 2x for
the first 8 hours and 3x after; Off Day pays a flat 2x; on rest, off and
public-holiday days the minimum must be met before any OT counts. All of
it from the deploy date only — "so we dont harm old existing data".

Every deploy recounts unpaid OT in the filing window with the rates as
they stand (backfill_ot_after_rounding_rule.run_repairs), so a rate table
edited in place would reprice those old days. Each rate row now carries an
Effective From date; a day is priced by the newest rows on or before it.

Expected values are the owner's own examples at RM10/hour.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_ot_rates_from_a_date.py
"""

import ast
import pathlib
import sys
import unittest
from datetime import date
from itertools import pairwise
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

from hrms.utils import ot_calculation as ot

POLICY_DAY = date(2026, 9, 29)
BEFORE = date(2026, 9, 28)
AFTER = date(2026, 10, 3)

OLD = {
	"normal": [(0.0, 24.0, 1.5)],
	"rest": [(0.0, 24.0, 2.0)],
	"off": [(0.0, 4.0, 1.5), (4.0, 24.0, 2.0)],
	"public_holiday": [(0.0, 24.0, 3.0)],
}
NEW = {
	"public_holiday": [(0.0, 8.0, 2.0), (8.0, 24.0, 3.0)],
	"off": [(0.0, 24.0, 2.0)],
}


def config(min_minutes=60):
	return {
		"min_minutes": min_minutes,
		"days_per_month": 26,
		"hours_per_day": 8,
		# blank Effective From = since always; the new rows start on POLICY_DAY
		"dated_bands": {
			None: OLD,
			POLICY_DAY: NEW,
		},
		# HR Settings: the minimum judges rest/off/PH days from this date
		"nonwork_minimum_from": POLICY_DAY,
		"daily_cap": 0.0,
		"monthly_cap": 0.0,
	}


def pay(hours, day_type, day):
	cfg = config()
	return sum(b["amount"] for b in ot._ot_bands_for_day(hours, 10.0, day_type, ot.bands_on(cfg, day)))


class TestPublicHoliday(unittest.TestCase):
	def test_ten_hours_after_the_change(self):
		self.assertEqual(pay(10, "public_holiday", AFTER), 220.0)  # 8x2 + 2x3

	def test_six_hours_after_the_change(self):
		self.assertEqual(pay(6, "public_holiday", AFTER), 120.0)

	def test_a_day_before_the_change_keeps_the_old_price(self):
		self.assertEqual(pay(10, "public_holiday", BEFORE), 300.0)

	def test_the_change_day_itself_is_new(self):
		self.assertEqual(pay(10, "public_holiday", POLICY_DAY), 220.0)


class TestOffDay(unittest.TestCase):
	def test_six_hours_after_the_change_is_flat_2x(self):
		self.assertEqual(pay(6, "off", AFTER), 120.0)

	def test_six_hours_before_the_change_keeps_the_old_split(self):
		self.assertEqual(pay(6, "off", BEFORE), 100.0)  # 4x1.5 + 2x2


class TestUnchangedDayTypes(unittest.TestCase):
	"""Rows the new date does not name carry on from the older set."""

	def test_rest_day(self):
		self.assertEqual(pay(5, "rest", AFTER), 100.0)

	def test_work_day(self):
		self.assertEqual(pay(2, "normal", AFTER), 30.0)


class TestMinimumOnNonWorkDays(unittest.TestCase):
	"""The minimum now judges rest/off/PH days too, from the same date."""

	def test_forty_minutes_on_a_rest_day_is_nothing_after_the_change(self):
		self.assertFalse(ot.day_qualifies(40 / 60, "rest", config(), AFTER))

	def test_fifty_five_minutes_rounds_to_the_hour_and_counts(self):
		self.assertTrue(ot.day_qualifies(55 / 60, "rest", config(), AFTER))

	def test_forty_minutes_on_a_rest_day_before_the_change_still_counts(self):
		self.assertTrue(ot.day_qualifies(40 / 60, "rest", config(), BEFORE))

	def test_no_date_set_leaves_non_work_days_as_they_were(self):
		cfg = {**config(), "nonwork_minimum_from": None}
		self.assertTrue(ot.day_qualifies(40 / 60, "rest", cfg, AFTER))

	def test_no_overtime_never_qualifies(self):
		self.assertFalse(ot.day_qualifies(0, "rest", config(), BEFORE))

	def test_work_day_minimum_is_unchanged_either_side(self):
		self.assertFalse(ot.day_qualifies(40 / 60, "normal", config(), BEFORE))
		self.assertFalse(ot.day_qualifies(40 / 60, "normal", config(), AFTER))


class TestEmptySettingIsNotAnAncientDate(unittest.TestCase):
	"""Found on the test site: get_single_value reads an EMPTY Date setting as
	0001-01-01. Taken at face value, the minimum would judge every rest day
	since the year 1 — repricing all the old days. Empty must stay empty."""

	def _read(self, stored):
		from unittest.mock import patch

		rows = ((stored,),) if stored is not None else ()
		with patch.object(ot.frappe.db, "sql", return_value=rows):
			return ot._nonwork_minimum_from()

	def test_empty_is_none(self):
		self.assertIsNone(self._read(None))
		self.assertIsNone(self._read(""))

	def test_a_set_date_is_that_date(self):
		self.assertEqual(self._read("2026-09-29"), POLICY_DAY)


class TestADayMustBeChosen(unittest.TestCase):
	"""Review, 28 Sep 2026: a shift's config carried today's rates as well, so a
	caller that skipped bands_on would price an OLD day at today's rates — the
	exact repricing this change prevents. Pricing now refuses such a config."""

	def test_pricing_a_shift_config_without_a_day_is_refused(self):
		with self.assertRaises(ValueError):
			ot._ot_bands_for_day(10, 10.0, "public_holiday", config())

	def test_pricing_the_day_chosen_config_works(self):
		self.assertEqual(pay(10, "public_holiday", AFTER), 220.0)


class TestOldStyleConfig(unittest.TestCase):
	"""A config with no dated rows (every caller before this change) is untouched."""

	def test_bands_on_passes_it_through(self):
		cfg = {"bands": OLD}
		self.assertIs(ot.bands_on(cfg, AFTER), cfg)


SHIFT = pathlib.Path(__file__).resolve().parents[1] / "hr/doctype/shift_type/shift_type.py"


class _Refused(Exception):
	pass


def _validate_rates(rows):
	"""Run ShiftType.validate_overtime_rates on these rows, as the real method."""
	tree = ast.parse(SHIFT.read_text())
	cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ShiftType")
	fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "validate_overtime_rates")
	frappe = MagicMock()
	frappe.throw.side_effect = lambda msg, *a, **k: (_ for _ in ()).throw(_Refused(msg))
	frappe.bold = str
	ns = {"frappe": frappe, "_": lambda s: s, "pairwise": pairwise, "getdate": ot.getdate}
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SHIFT), "exec"), ns)

	def row(i, day_type, from_hour, to_hour, rate, since=None):
		return SimpleNamespace(
			idx=i + 1,
			day_type=day_type,
			from_hour=from_hour,
			from_minute=0,
			to_hour=to_hour,
			to_minute=0 if to_hour < 23 else 59,
			rate=rate,
			effective_from=since,
			get=lambda f: since if f == "effective_from" else None,
		)

	doc = SimpleNamespace(
		enable_overtime=1,
		overtime_rates=[row(i, *r) for i, r in enumerate(rows)],
		is_new=lambda: False,
		has_value_changed=lambda f: False,
	)
	ns["validate_overtime_rates"](doc)


class TestShiftTypeAcceptsDatedRates(unittest.TestCase):
	"""Old and new Public Holiday rows side by side are two tables, not an overlap."""

	def test_old_and_new_public_holiday_rows_are_accepted(self):
		_validate_rates(
			[
				("Public Holiday", 0, 23, 3.0),
				("Public Holiday", 0, 8, 2.0, "2026-09-29"),
				("Public Holiday", 8, 23, 3.0, "2026-09-29"),
			]
		)

	def test_an_overlap_inside_one_date_is_still_refused(self):
		with self.assertRaises(_Refused):
			_validate_rates(
				[
					("Public Holiday", 0, 8, 2.0, "2026-09-29"),
					("Public Holiday", 6, 23, 3.0, "2026-09-29"),
				]
			)

	def test_a_gap_inside_one_date_is_still_refused(self):
		with self.assertRaises(_Refused):
			_validate_rates(
				[
					("Public Holiday", 0, 6, 2.0, "2026-09-29"),
					("Public Holiday", 8, 23, 3.0, "2026-09-29"),
				]
			)


if __name__ == "__main__":
	unittest.main()

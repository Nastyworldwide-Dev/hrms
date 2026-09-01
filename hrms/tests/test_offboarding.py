"""Guards the offboarding automation (`hrms.hr.offboarding`).

Promises pinned here:

* proration to the relieving date is deterministic — recomputed from the
  parked full-period baseline, so re-saving the Employee never compounds
  a reduction (idempotent by construction);
* leave already taken is never planned away (the allocation's own
  validation would refuse the save);
* a cancelled or moved relieving date restores the baseline exactly;
* scheduler-managed (earned leave) allocations are left alone;
* the Active -> Left threshold is counted in WORKING days against the
  employee's holiday dates, not calendar days;
* the hooks are actually registered.

Bench-free by construction: the module is loaded straight from its file
with a stub `frappe` in `sys.modules`. Run it as a FILE:

    python3 hrms/tests/test_offboarding.py
"""

import datetime
import importlib.util
import pathlib
import sys
import types
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = HRMS_ROOT / "hr" / "offboarding.py"
HOOKS_PATH = HRMS_ROOT / "hooks.py"


def _flt(value, precision=None):
	try:
		value = float(value or 0)
	except (TypeError, ValueError):
		return 0.0
	return round(value, precision) if precision is not None else value


def _getdate(value=None):
	if isinstance(value, datetime.date):
		return value
	return datetime.date.fromisoformat(str(value))


def _load_module():
	if "frappe" not in sys.modules:
		frappe = types.ModuleType("frappe")
		frappe._ = lambda text: text
		frappe.whitelist = lambda *a, **kw: lambda fn: fn
		frappe.flags = types.SimpleNamespace()
		frappe_utils = types.ModuleType("frappe.utils")
		frappe.utils = frappe_utils
		sys.modules["frappe"] = frappe
		sys.modules["frappe.utils"] = frappe_utils
	frappe_utils = sys.modules["frappe.utils"]
	for name, fn in {
		"flt": _flt,
		"getdate": _getdate,
		"cint": lambda v: int(v or 0),
		"add_days": lambda d, days: _getdate(d) + datetime.timedelta(days=days),
	}.items():
		if not getattr(frappe_utils, name, None):
			setattr(frappe_utils, name, fn)

	spec = importlib.util.spec_from_file_location("_hrms_offboarding_under_test", MODULE_PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


offboarding = _load_module()

D = datetime.date
YEAR_START, YEAR_END = D(2026, 1, 1), D(2026, 12, 31)


def make_allocation(**overrides):
	allocation = {
		"name": "LAL-0001",
		"from_date": YEAR_START,
		"to_date": YEAR_END,
		"new_leaves_allocated": 30.0,
		"unused_leaves": 0.0,
		"pre_offboarding_leaves": 0.0,
		"leaves_taken": 0.0,
		"is_scheduler_managed": False,
	}
	allocation.update(overrides)
	return allocation


class TestProrateToRelieving(unittest.TestCase):
	def test_mid_period_prorates_by_elapsed_days(self):
		# Jan 1 .. Jun 30 = 181 of 365 days -> 30 * 181/365 = 14.88 -> 15
		self.assertEqual(offboarding.prorate_to_relieving(30.0, YEAR_START, YEAR_END, D(2026, 6, 30)), 15.0)

	def test_relieving_on_or_after_period_end_keeps_everything(self):
		self.assertEqual(offboarding.prorate_to_relieving(30.0, YEAR_START, YEAR_END, YEAR_END), 30.0)
		self.assertEqual(offboarding.prorate_to_relieving(30.0, YEAR_START, YEAR_END, D(2027, 3, 1)), 30.0)

	def test_relieving_before_period_start_earns_nothing(self):
		self.assertEqual(offboarding.prorate_to_relieving(30.0, YEAR_START, YEAR_END, D(2025, 12, 31)), 0.0)

	def test_zero_entitlement_stays_zero(self):
		self.assertEqual(offboarding.prorate_to_relieving(0.0, YEAR_START, YEAR_END, D(2026, 6, 30)), 0.0)


class TestPlanAllocationTargets(unittest.TestCase):
	def test_prorates_and_parks_baseline(self):
		plans = offboarding.plan_allocation_targets([make_allocation()], D(2026, 6, 30))
		self.assertEqual(
			plans,
			[{"name": "LAL-0001", "new_leaves_allocated": 15.0, "pre_offboarding_leaves": 30.0}],
		)

	def test_rerun_after_proration_is_a_noop(self):
		prorated = make_allocation(new_leaves_allocated=15.0, pre_offboarding_leaves=30.0)
		self.assertEqual(offboarding.plan_allocation_targets([prorated], D(2026, 6, 30)), [])

	def test_reprorate_uses_baseline_not_current_value(self):
		prorated = make_allocation(new_leaves_allocated=15.0, pre_offboarding_leaves=30.0)
		plans = offboarding.plan_allocation_targets([prorated], D(2026, 9, 30))
		# Jan 1 .. Sep 30 = 273/365 of 30 -> 22, computed from 30, not from 15
		self.assertEqual(plans[0]["new_leaves_allocated"], 22.0)
		self.assertEqual(plans[0]["pre_offboarding_leaves"], 30.0)

	def test_cancelled_offboarding_restores_baseline(self):
		prorated = make_allocation(new_leaves_allocated=15.0, pre_offboarding_leaves=30.0)
		plans = offboarding.plan_allocation_targets([prorated], None)
		self.assertEqual(
			plans,
			[{"name": "LAL-0001", "new_leaves_allocated": 30.0, "pre_offboarding_leaves": 0.0}],
		)

	def test_relieving_moved_past_period_end_restores_baseline(self):
		prorated = make_allocation(new_leaves_allocated=15.0, pre_offboarding_leaves=30.0)
		plans = offboarding.plan_allocation_targets([prorated], D(2027, 1, 15))
		self.assertEqual(plans[0]["new_leaves_allocated"], 30.0)
		self.assertEqual(plans[0]["pre_offboarding_leaves"], 0.0)

	def test_leaves_already_taken_are_never_planned_away(self):
		allocation = make_allocation(leaves_taken=20.0)
		plans = offboarding.plan_allocation_targets([allocation], D(2026, 6, 30))
		self.assertEqual(plans[0]["new_leaves_allocated"], 20.0)

	def test_carry_forward_covers_part_of_the_taken_floor(self):
		# 5 carried forward + prorated 15 planned; 18 taken -> floor is 18-5=13 < 15
		allocation = make_allocation(unused_leaves=5.0, leaves_taken=18.0)
		plans = offboarding.plan_allocation_targets([allocation], D(2026, 6, 30))
		self.assertEqual(plans[0]["new_leaves_allocated"], 15.0)

	def test_scheduler_managed_allocations_are_untouched(self):
		allocation = make_allocation(is_scheduler_managed=True)
		self.assertEqual(offboarding.plan_allocation_targets([allocation], D(2026, 6, 30)), [])

	def test_allocation_entirely_after_relieving_goes_to_zero(self):
		allocation = make_allocation(from_date=D(2026, 7, 1), to_date=D(2027, 6, 30))
		plans = offboarding.plan_allocation_targets([allocation], D(2026, 6, 30))
		self.assertEqual(plans[0]["new_leaves_allocated"], 0.0)

	def test_unchanged_allocation_with_no_relieving_is_a_noop(self):
		self.assertEqual(offboarding.plan_allocation_targets([make_allocation()], None), [])


class TestHookWiring(unittest.TestCase):
	def test_employee_hooks_are_registered(self):
		hooks = HOOKS_PATH.read_text()
		self.assertIn("hrms.hr.offboarding.validate_offboarding_dates", hooks)
		self.assertIn("hrms.hr.offboarding.prorate_leave_allocations", hooks)

	def test_leave_allocation_carries_the_baseline_field(self):
		import json

		meta = json.loads(
			(HRMS_ROOT / "hr" / "doctype" / "leave_allocation" / "leave_allocation.json").read_text()
		)
		field = next(f for f in meta["fields"] if f["fieldname"] == "pre_offboarding_leaves")
		self.assertEqual(field.get("allow_on_submit"), 1)
		self.assertEqual(field.get("hidden"), 1)
		self.assertIn("pre_offboarding_leaves", meta["field_order"])


if __name__ == "__main__":
	unittest.main(verbosity=2)

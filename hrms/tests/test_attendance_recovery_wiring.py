"""The lost-OT release wires itself: switches for HR, one run after deploy, nightly after.

PYTHONPATH=. python3 hrms/tests/test_attendance_recovery_wiring.py
"""

import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path[:0] = [
	str(pathlib.Path(__file__).resolve().parents[2]),
	str(pathlib.Path(__file__).resolve().parent),
]
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

HRMS = pathlib.Path(__file__).resolve().parents[1]


class TestSwitches(unittest.TestCase):
	def test_every_automatic_step_and_the_erp_closer_have_a_switch_the_code_reads(self):
		from hrms.patches.v16_0.attendance_recovery_switches import fields
		from hrms.sync.lone_in_closer import SETTING
		from hrms.utils.attendance_auto_recovery import AUTO_STEPS, SWITCH_PREFIX

		names = {f["fieldname"] for f in fields()}
		for step in AUTO_STEPS:
			self.assertIn(SWITCH_PREFIX + step, names, step)
		self.assertIn(SWITCH_PREFIX + "recheck", names)
		self.assertIn(SETTING, names)

	def test_switches_default_to_running(self):
		from hrms.patches.v16_0.attendance_recovery_switches import fields

		for f in fields():
			if f["fieldname"].startswith("attendance_recovery_skip_"):
				self.assertEqual(f["default"], "0", f["fieldname"])
		closer = next(f for f in fields() if f["fieldname"] == "attendance_close_lone_ins_from_erp")
		self.assertEqual(closer["default"], "1")


class TestEndgameSwitches(unittest.TestCase):
	"""Part A and Part B write nothing until HR ticks their switch, and a pilot
	list can hold them to a few employees first (Nabil, 16 Sep 2026)."""

	def _fields(self):
		from hrms.patches.v16_0.attendance_recovery_switches import fields

		return {f["fieldname"]: f for f in fields()}

	def test_the_two_write_switches_exist_and_start_off(self):
		fields = self._fields()
		for name in ("attendance_ownership_relabel", "attendance_erp_backfill"):
			self.assertEqual(fields[name]["fieldtype"], "Check", name)
			self.assertEqual(fields[name]["default"], "0", name)

	def test_a_pilot_list_can_hold_them_to_a_few_employees(self):
		field = self._fields()["attendance_rebuild_pilot_employees"]
		self.assertEqual(field["fieldtype"], "Small Text")
		self.assertIn("empty = everyone", field["label"])


class TestOnceAndNightly(unittest.TestCase):
	def test_v2_patch_only_enqueues_the_full_run(self):
		from hrms.patches.v16_0 import run_attendance_recovery_v2_once as p

		with patch.object(frappe, "enqueue", MagicMock()) as enqueue:
			p.execute()
		self.assertEqual(enqueue.call_args.args[0], "hrms.utils.attendance_auto_recovery.run_once")
		self.assertEqual(enqueue.call_args.kwargs["queue"], "long")

	def test_both_patches_registered_once_after_the_first_run(self):
		lines = [
			l.split()[0] for l in (HRMS / "patches.txt").read_text().splitlines() if l.startswith("hrms.")
		]
		v1 = lines.index("hrms.patches.v16_0.run_attendance_recovery_once")
		sw = lines.index("hrms.patches.v16_0.attendance_recovery_switches")
		v2 = lines.index("hrms.patches.v16_0.run_attendance_recovery_v2_once")
		self.assertTrue(v1 < sw < v2)
		self.assertEqual(lines.count("hrms.patches.v16_0.run_attendance_recovery_v2_once"), 1)


if __name__ == "__main__":
	unittest.main()

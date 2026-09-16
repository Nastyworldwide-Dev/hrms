"""The repair switches are EMERGENCY STOPS, not start gates — Nabil, 16 Sep 2026.

"too much mechanical work for us and for HR — it should be done automatically by
the system at once". A switch whose Custom Field has not been created yet used to
read as OFF, so a fresh deploy relabelled nothing and copied no punch until a
person went into HR Settings and ticked two boxes. That is the mechanical work
the owner refused.

Both switches now read as ON while nothing says otherwise. HR turns one OFF to
stop the machine; HR never has to turn one ON to start it.

	PYTHONPATH=. python3 hrms/tests/test_attendance_switch_defaults.py
"""

import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path[:0] = [
	str(pathlib.Path(__file__).resolve().parents[2]),
	str(pathlib.Path(__file__).resolve().parent),
]
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.sync import erp_backfill as backfill
from hrms.utils import attendance_ownership as own


def _settings(values):
	"""HR Settings holding exactly `values`; anything else is an absent field."""
	return lambda doctype: SimpleNamespace(get=lambda key, default=None: values.get(key, default))


class TestRelabelSwitch(unittest.TestCase):
	def test_runs_while_the_custom_field_does_not_exist(self):
		with patch.object(frappe, "get_single", _settings({}), create=True):
			self.assertTrue(own.relabel_enabled())

	def test_runs_while_the_field_exists_and_nobody_stopped_it(self):
		with patch.object(frappe, "get_single", _settings({own.RELABEL_SWITCH: 1}), create=True):
			self.assertTrue(own.relabel_enabled())

	def test_stops_only_when_hr_unticks_it(self):
		with patch.object(frappe, "get_single", _settings({own.RELABEL_SWITCH: 0}), create=True):
			self.assertFalse(own.relabel_enabled())

	def test_an_unreadable_settings_row_is_not_a_stop(self):
		def boom(doctype):
			raise RuntimeError("HR Settings is locked")

		with patch.object(frappe, "get_single", boom, create=True):
			self.assertTrue(own.relabel_enabled())

	def test_an_empty_pilot_list_means_everyone(self):
		with patch.object(frappe, "get_single", _settings({}), create=True):
			self.assertEqual(own.pilot_employees(), [])


class TestErpBackfillSwitch(unittest.TestCase):
	def test_runs_while_the_custom_field_does_not_exist(self):
		with patch.object(frappe, "get_single", _settings({}), create=True):
			self.assertTrue(backfill._enabled())

	def test_runs_while_the_field_exists_and_nobody_stopped_it(self):
		with patch.object(frappe, "get_single", _settings({backfill.SWITCH: 1}), create=True):
			self.assertTrue(backfill._enabled())

	def test_stops_only_when_hr_unticks_it(self):
		with patch.object(frappe, "get_single", _settings({backfill.SWITCH: 0}), create=True):
			self.assertFalse(backfill._enabled())

	def test_an_unreadable_settings_row_is_not_a_stop(self):
		def boom(doctype):
			raise RuntimeError("HR Settings is locked")

		with patch.object(frappe, "get_single", boom, create=True):
			self.assertTrue(backfill._enabled())

	def test_an_empty_pilot_list_means_everyone(self):
		self.assertIsNone(backfill.pilot_employees("", None))


if __name__ == "__main__":
	unittest.main(verbosity=2)

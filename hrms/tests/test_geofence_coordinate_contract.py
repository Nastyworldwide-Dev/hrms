"""Public preview and actual checkin validator reject invalid coordinates, including NaN."""

import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.api import geofence as api
from hrms.overrides import employee_checkin_override as override
from hrms.overrides.test_employee_checkin_override import _FakeCheckin, _patched


class TestCoordinateContract(unittest.TestCase):
	def test_zero_coordinates_are_valid_on_actual_checkin_validator(self):
		doc = _FakeCheckin(latitude=0, longitude=0)
		patches = _patched(distance_m=0)
		for item in patches:
			item.start()
		try:
			override.CustomEmployeeCheckin.validate_distance_from_shift_location(doc)
		finally:
			for item in reversed(patches):
				item.stop()
		self.assertEqual(doc.requires_remote_approval, 0)

	def test_invalid_coordinates_cannot_enter_preview_or_insert_distance_calculation(self):
		for latitude, longitude in [
			(float("nan"), 101.5),
			(float("inf"), 101.5),
			(91, 101.5),
			(3, -181),
			(None, 101.5),
		]:
			with self.subTest(latitude=latitude, longitude=longitude):
				with (
					patch.object(api, "_ensure_own_employee_or_permitted"),
					patch.object(api, "is_setting_enabled_for_employee", return_value=True),
					patch.object(api, "resolve_assignment", return_value=None),
					patch.object(api, "employee_now", return_value=datetime(2026, 9, 3)),
					patch.object(api, "get_distance_between_coordinates") as distance,
				):
					with self.assertRaises(frappe.ValidationError):
						api.check_geofence("EMP", "IN", latitude, longitude)
					distance.assert_not_called()
				with (
					patch.object(override, "is_setting_enabled_for_employee", return_value=True),
					patch.object(override, "get_distance_between_coordinates") as distance,
				):
					with self.assertRaises(frappe.ValidationError):
						override.CustomEmployeeCheckin.validate_distance_from_shift_location(
							_FakeCheckin(latitude=latitude, longitude=longitude, shift=None)
						)
					distance.assert_not_called()

	def test_missing_location_keeps_strict_policy_in_preview_context(self):
		assignment = SimpleNamespace(enable_strict_geofence=1, shift_type="DAY")
		with (
			patch.object(api, "_ensure_own_employee_or_permitted"),
			patch.object(api, "resolve_assignment", return_value=assignment),
			patch.object(api, "effective_shift_location", return_value=None),
			patch.object(api, "employee_now", return_value=datetime(2026, 9, 3)),
		):
			result = api.get_active_shift_location("EMP")
		self.assertIsNotNone(result)
		self.assertTrue(result["strict"])
		self.assertFalse(result["has_shift_location"])

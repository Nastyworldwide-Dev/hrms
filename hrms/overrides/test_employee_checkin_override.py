# Copyright (c) 2026, Nastyworldwide and contributors
# See license.txt
"""Regression tests for the geofence wiring on CustomEmployeeCheckin.

The decision itself is unit-tested in `hrms.utils.test_geofence`. What is
tested here is the part that a refactor drops without any test noticing: that
the device's reported accuracy actually travels from the punch request to the
decision. An accuracy that is collected, sent, stored and then not passed to
`evaluate_geofence` looks exactly like a working feature from the outside,
and measures the fence as if every reading were surveyed.

Pure unit tests: no bench, no site, no DB — the method is called unbound
against a stand-in document and every collaborator is patched. Run with
`python -m unittest hrms.overrides.test_employee_checkin_override` from the
repo root with a frappe-importable interpreter, as well as under
`bench run-tests`.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import hrms.overrides.employee_checkin_override as mod

MODULE = "hrms.overrides.employee_checkin_override"


class _FakeCheckin(SimpleNamespace):
	"""Stands in for an Employee Checkin document being validated."""

	def __init__(self, **kwargs):
		defaults = {
			"name": None,
			"employee": "EMP-0001",
			"log_type": "IN",
			"time": "2026-08-24 09:00:00",
			"shift": "Day Shift",
			"latitude": 3.1,
			"longitude": 101.6,
			"device_id": None,
			"requires_remote_approval": 0,
			"remote_approval_status": None,
			"flags": SimpleNamespace(),
		}
		defaults.update(kwargs)
		super().__init__(**defaults)


def _patched(distance_m=120.0, radius=100, strict=False):
	"""Every collaborator of validate_distance_from_shift_location, stubbed."""
	assignment = SimpleNamespace(shift_location="KL Office", enable_strict_geofence=int(strict))
	location = SimpleNamespace(checkin_radius=radius, latitude=3.0, longitude=101.5)
	return [
		patch(f"{MODULE}.is_setting_enabled_for_employee", return_value=True),
		patch(f"{MODULE}.resolve_assignment", return_value=assignment),
		patch(f"{MODULE}.resolve_location", return_value=location),
		patch(f"{MODULE}.get_distance_between_coordinates", return_value=distance_m),
		patch(f"{MODULE}._record_geofence_reject"),
	]


class TestAccuracyReachesTheDecision(unittest.TestCase):
	def _run(self, doc, **kw):
		"""Validate `doc` with collaborators stubbed; return the spy on the decision."""
		with patch(f"{MODULE}.evaluate_geofence", return_value=None) as spy:
			patches = _patched(**kw)
			for p in patches:
				p.start()
			try:
				mod.CustomEmployeeCheckin.validate_distance_from_shift_location(doc)
			finally:
				for p in patches:
					p.stop()
		return spy

	def test_reported_accuracy_is_passed_to_the_decision(self):
		doc = _FakeCheckin(flags=SimpleNamespace(location_accuracy_m=42.0))
		spy = self._run(doc)
		self.assertEqual(spy.call_args.kwargs["accuracy_m"], 42.0)

	def test_a_punch_carrying_no_accuracy_reports_it_as_unknown(self):
		# Biometric device rows and Desk entries have no browser behind them.
		# They must arrive as None (no allowance), never as 0 (perfect fix).
		doc = _FakeCheckin()
		spy = self._run(doc)
		self.assertIsNone(spy.call_args.kwargs["accuracy_m"])


class TestImpreciseReadingEndToEnd(unittest.TestCase):
	"""The real decision, through the real method — lenient mode only.

	Strict mode ends in frappe.throw, which needs a request context; its
	branches are covered by the pure tests in hrms.utils.test_geofence.
	"""

	def test_unplaceable_reading_goes_to_an_approver_even_when_it_reads_inside(self):
		# 10 m from the office by a fix that is only sure to +/-5 km: the
		# number says "inside" and means nothing. Before the allowance existed
		# this was a silent, unreviewable accept.
		doc = _FakeCheckin(flags=SimpleNamespace(location_accuracy_m=5000))
		patches = _patched(distance_m=10.0)
		for p in patches:
			p.start()
		try:
			mod.CustomEmployeeCheckin.validate_distance_from_shift_location(doc)
		finally:
			for p in patches:
				p.stop()

		self.assertEqual(doc.requires_remote_approval, 1)
		self.assertEqual(doc.remote_approval_status, "Pending")
		self.assertEqual(doc._remote_nearest_location, "KL Office")

	def test_a_fix_inside_its_own_error_bar_is_not_sent_to_an_approver(self):
		# 120 m out, +/-40 m — the doorstep. This is the every-morning case
		# that used to generate an approval request per employee per punch.
		doc = _FakeCheckin(flags=SimpleNamespace(location_accuracy_m=40))
		patches = _patched(distance_m=120.0)
		for p in patches:
			p.start()
		try:
			mod.CustomEmployeeCheckin.validate_distance_from_shift_location(doc)
		finally:
			for p in patches:
				p.stop()

		self.assertEqual(doc.requires_remote_approval, 0)
		self.assertIsNone(doc.remote_approval_status)


class TestGeofenceRejectLogDurability(unittest.TestCase):
	"""A strict rejection throws, and the throw rolls back the request
	transaction — the same one that wrote the Geofence Reject Log. Bench-verified
	that without an explicit commit the row is gone after the rollback, which is
	why production carried zero reject logs despite every rejection writing one.
	_record_geofence_reject must commit the audit row so it survives the throw.
	"""

	def _ctx(self):
		return {
			"reason": mod.REASON_OUTSIDE_RADIUS,
			"distance_m": 6937.0,
			"radius_m": 100,
			"overshoot_m": 6837.0,
			"accuracy_m": 10.0,
		}

	def test_reject_log_is_committed_so_it_survives_the_rollback(self):
		doc = _FakeCheckin()
		saved = mod.frappe.flags.in_test
		with patch(f"{MODULE}.frappe.new_doc"), patch(f"{MODULE}.frappe.db.commit") as commit:
			# The production path is `not in_test`; the runner sets in_test True,
			# which is exactly the branch that skips the commit for test isolation.
			mod.frappe.flags.in_test = False
			try:
				mod._record_geofence_reject(doc, self._ctx(), "KL Office")
			finally:
				mod.frappe.flags.in_test = saved
		commit.assert_called_once()

	def test_reject_log_does_not_commit_under_the_test_runner(self):
		# The isolation guard: inside the runner the commit must be skipped, or it
		# would persist other tests' fixtures past their rolled-back transaction.
		doc = _FakeCheckin()
		with patch(f"{MODULE}.frappe.new_doc"), patch(f"{MODULE}.frappe.db.commit") as commit:
			mod.frappe.flags.in_test = True
			mod._record_geofence_reject(doc, self._ctx(), "KL Office")
		commit.assert_not_called()


if __name__ == "__main__":
	unittest.main()

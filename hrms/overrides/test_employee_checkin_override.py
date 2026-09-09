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

import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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


class TestOverrideImportBoundary(unittest.TestCase):
	def test_override_and_employee_controller_are_real_python_classes(self):
		self.assertIsInstance(mod.EmployeeCheckin, type)
		self.assertIsInstance(mod.CustomEmployeeCheckin, type)
		self.assertTrue(issubclass(mod.CustomEmployeeCheckin, mod.EmployeeCheckin))


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
	"""The native DB suite proves durability; here exercise all cleanup failures."""

	def test_only_isolated_connection_commits_and_all_context_is_restored(self):
		for failure in (None, "connect", "insert", "commit", "rollback", "close"):
			with self.subTest(failure=failure):
				caller, isolated, log = MagicMock(), MagicMock(), MagicMock()
				flags = mod.frappe._dict(in_test=True, currently_saving=[("caller", "document")])
				realtime, messages = ["caller event"], ["caller message"]
				local = SimpleNamespace(db=caller, flags=flags, _realtime_log=realtime, message_log=messages)
				factory = MagicMock(return_value=isolated)
				if failure == "connect":
					factory.side_effect = RuntimeError("synthetic connect failure")
				if failure in ("insert", "rollback"):
					log.insert.side_effect = ValueError("synthetic insertion failure")
				if failure in ("commit", "rollback", "close"):
					getattr(isolated, failure).side_effect = RuntimeError("synthetic cleanup failure")

				def insert_context():
					self.assertIs(local.db, isolated)
					self.assertIsNot(local.flags, flags)
					local.flags.currently_saving.append(("audit", "document"))
					local._realtime_log = ["audit event"]
					local.message_log.append("audit message")
					return log

				with (
					patch.dict(sys.modules, {"frappe.database": SimpleNamespace(get_db=factory)}),
					patch.object(mod.frappe, "local", local),
					patch.object(mod.frappe, "new_doc", side_effect=lambda *_: insert_context()),
				):
					mod._record_geofence_reject(_FakeCheckin(), {"reason": mod.REASON_OUTSIDE_RADIUS}, None)
				self.assertIs(local.db, caller)
				self.assertIs(local.flags, flags)
				self.assertEqual(flags.currently_saving, [("caller", "document")])
				self.assertIs(local._realtime_log, realtime)
				self.assertIs(local.message_log, messages)
				caller.commit.assert_not_called()
				caller.rollback.assert_not_called()
				caller.close.assert_not_called()
				if failure != "connect":
					isolated.close.assert_called_once()
				if failure is None:
					isolated.commit.assert_called_once()
					isolated.rollback.assert_not_called()
				elif failure in ("insert", "commit", "rollback"):
					isolated.rollback.assert_called_once()


class TestFreeLocationOnInsert(unittest.TestCase):
	"""A punch against a free Shift Location is recorded as-is, even strict."""

	def _run(self, doc, **kw):
		assignment = SimpleNamespace(shift_location="Field Sales", enable_strict_geofence=1)
		location = SimpleNamespace(
			is_free_location=1, checkin_radius=kw.get("radius", 0), latitude=None, longitude=None
		)
		patches = [
			patch(f"{MODULE}.is_setting_enabled_for_employee", return_value=True),
			patch(f"{MODULE}.resolve_assignment", return_value=assignment),
			patch(f"{MODULE}.resolve_location", return_value=location),
			patch(f"{MODULE}.get_distance_between_coordinates", return_value=250_000.0),
			patch(f"{MODULE}._record_geofence_reject"),
		]
		for p in patches:
			p.start()
		try:
			mod.CustomEmployeeCheckin.validate_distance_from_shift_location(doc)
		finally:
			for p in patches:
				p.stop()

	def test_strict_free_location_far_away_records_without_approval(self):
		doc = _FakeCheckin(flags=SimpleNamespace(location_accuracy_m=30))
		self._run(doc)
		self.assertEqual(doc.requires_remote_approval, 0)
		self.assertIsNone(doc.remote_approval_status)

	def test_the_flag_reaches_the_decision(self):
		doc = _FakeCheckin()
		with patch(f"{MODULE}.evaluate_geofence", return_value=None) as spy:
			self._run(doc)
		self.assertTrue(spy.call_args.kwargs.get("free_location"))


if __name__ == "__main__":
	unittest.main()

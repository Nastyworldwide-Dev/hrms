"""Opt-in real database regression with owned synthetic fixtures only.

From the bench sites directory: NADI_GEOFENCE_TEST_SITE=test.local
<bench>/env/bin/python <app>/hrms/tests/test_geofence_audit_transaction.py
"""

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
	import frappe
	from frappe.model.document import Document
except ModuleNotFoundError as exc:
	raise unittest.SkipTest("Real Frappe and explicit NADI_GEOFENCE_TEST_SITE required") from exc
if not isinstance(Document, type) or Document.__module__ != "frappe.model.document":
	raise unittest.SkipTest("Real Frappe required; stub cannot test transaction isolation")
if not os.environ.get("NADI_GEOFENCE_TEST_SITE"):
	raise unittest.SkipTest("Set NADI_GEOFENCE_TEST_SITE to an explicitly authorized local test site")

from hrms.overrides import employee_checkin_override as mod


class TestGeofenceAuditTransaction(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		frappe.init(site=os.environ["NADI_GEOFENCE_TEST_SITE"])
		frappe.connect()
		cls.employee = "GPS-TXN-" + uuid4().hex
		frappe.get_doc(
			{
				"doctype": "Employee",
				"name": cls.employee,
				"employee_name": "Synthetic audit fixture",
				"first_name": "Synthetic",
			}
		).db_insert()
		frappe.get_doc({"doctype": "Shift Type", "name": cls.employee}).db_insert()
		frappe.db.commit()  # Only this explicitly created synthetic fixture.

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		frappe.db.delete("Geofence Reject Log", {"employee": cls.employee})
		frappe.db.delete("DefaultValue", {"parent": cls.employee})
		frappe.db.delete("Employee", {"name": cls.employee})
		frappe.db.delete("Shift Type", {"name": cls.employee})
		frappe.db.commit()  # Remove only this suite's synthetic records.
		for doctype, filters in (
			("Employee", {"name": cls.employee}),
			("Shift Type", {"name": cls.employee}),
			("DefaultValue", {"parent": cls.employee}),
			("Geofence Reject Log", {"employee": cls.employee}),
		):
			assert not frappe.db.exists(doctype, filters), f"Synthetic {doctype} cleanup failed"
		frappe.destroy()

	def test_strict_refusal_keeps_audit_but_rolls_back_caller_writes(self):
		for in_test, in_job in [(False, False), (False, True), (True, False)]:
			with self.subTest(in_test=in_test, in_job=in_job):
				frappe.db.rollback()
				marker = "GPS-MARKER-" + uuid4().hex
				frappe.get_doc(
					{
						"doctype": "DefaultValue",
						"name": marker,
						"parent": self.employee,
						"defkey": "synthetic",
						"defvalue": "rollback",
					}
				).db_insert()
				caller = frappe.local.db
				commits = []
				caller.after_commit.add(lambda: commits.append("caller"))
				flags = frappe.local.flags
				flags.in_test, flags.in_job = in_test, in_job
				frappe.publish_realtime("synthetic_caller_event", {}, after_commit=True)
				realtime = frappe.local._realtime_log
				messages = frappe.local.message_log
				before = frappe.db.count("Geofence Reject Log", {"employee": self.employee})
				doc = mod.CustomEmployeeCheckin(
					{
						"doctype": "Employee Checkin",
						"employee": self.employee,
						"log_type": "IN",
						"shift": self.employee,
						"time": "2026-09-08 09:00:00",
						"latitude": 3.1,
						"longitude": 101.6,
					}
				)
				doc.flags.location_accuracy_m = 10
				with (
					patch("frappe.realtime.emit_via_redis") as emit,
					patch.object(mod, "is_setting_enabled_for_employee", return_value=True),
					patch.object(
						mod,
						"resolve_assignment",
						return_value=SimpleNamespace(shift_location=None, enable_strict_geofence=1),
					),
					self.assertRaises(mod.CheckinRadiusExceededError),
				):
					doc.validate_distance_from_shift_location()
				self.assertIs(frappe.local.db, caller)
				self.assertIs(frappe.local.flags, flags)
				self.assertIs(frappe.local._realtime_log, realtime)
				self.assertIs(frappe.local.message_log, messages)
				self.assertNotIn("synthetic_caller_event", [call.args[0] for call in emit.call_args_list])
				frappe.db.rollback()
				self.assertFalse(
					frappe.db.exists("DefaultValue", marker), "caller marker committed by rejection"
				)
				self.assertEqual(commits, [], "caller commit callbacks ran during refusal")
				self.assertEqual(
					frappe.db.count("Geofence Reject Log", {"employee": self.employee}), before + 1
				)
				row = frappe.get_last_doc("Geofence Reject Log", filters={"employee": self.employee})
				self.assertEqual(row.reason, mod.REASON_NO_SHIFT_LOCATION)
				self.assertEqual((row.latitude, row.longitude), (3.1, 101.6))

	def test_audit_database_failure_cannot_replace_original_strict_refusal(self):
		from frappe.database import get_db

		for failure in ("connect", "insert", "commit"):
			with self.subTest(failure=failure):
				frappe.db.rollback()
				caller = frappe.local.db
				before = frappe.db.count("Geofence Reject Log", {"employee": self.employee})
				flags, messages = frappe.local.flags, frappe.local.message_log
				message_count = len(messages or [])
				connections = []

				def factory(**kwargs):
					if failure == "connect":
						raise RuntimeError("synthetic connect failure")
					db = get_db(**kwargs)
					connections.append(db)
					if failure == "commit":
						db.commit = lambda: (_ for _ in ()).throw(RuntimeError("synthetic commit failure"))
					return db

				doc = mod.CustomEmployeeCheckin(
					{
						"doctype": "Employee Checkin",
						"employee": self.employee,
						"shift": self.employee,
						"log_type": "IN",
						"time": "2026-09-08 09:00:00",
						"latitude": 3.1,
						"longitude": 101.6,
					}
				)
				# An invalid link forces real Document link validation to fail, after
				# connection creation. Existing committed fixtures remain untouched.
				if failure == "insert":
					doc.employee = "GPS-NONEXISTENT-" + uuid4().hex
				with (
					patch("frappe.database.get_db", side_effect=factory),
					self.assertRaises(mod.CheckinRadiusExceededError),
				):
					doc._throw_strict_geofence({"reason": mod.REASON_NO_SHIFT_LOCATION}, None)
				self.assertIs(frappe.local.db, caller)
				self.assertIs(frappe.local.flags, flags)
				# Only the authoritative refusal may reach the caller's messages;
				# an isolated LinkValidationError must not add a second error.
				self.assertEqual(len(frappe.local.message_log), message_count + 1)
				self.assertIn("Strict geofencing", frappe.local.message_log[-1]["message"])
				self.assertTrue(all(db._conn is None for db in connections), "isolated connection leaked")
				frappe.db.rollback()
				self.assertEqual(frappe.db.count("Geofence Reject Log", {"employee": self.employee}), before)


if __name__ == "__main__":
	unittest.main()

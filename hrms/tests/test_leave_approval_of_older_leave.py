"""An approver can approve a leave whose dates have passed ("Cannot approve
older leaves", employee issue, 15 Sep 2026).

`validate_dates` enforces HR Settings' "Restrict Backdated Leave Application"
on EVERY validate, and `hrms.api.approval.decide` approves by submitting the
document, which runs validate again — now with the approver's roles and with
"today" moved on. So a leave filed in time for the 10th and decided on the
15th read as backdated at decision time, and an approver outside the allowed
role was refused with "Only users with the X role can create backdated leave
applications" although nobody was creating anything. The setting governs who
may CREATE (or move) a backdated application; a decision on an existing one
changes no date.

Bench-free: the controller is imported under the frappe stub.
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_leave_approval_of_older_leave.py
"""

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
for module in ("pypika", "pypika.terms", "pypika.functions"):
	sys.modules.setdefault(module, MagicMock())
import frappe

from hrms.hr.doctype.leave_application import leave_application as la

TODAY = date(2026, 9, 15)
ALLOWED_ROLE = "HR Manager"


class _Refused(Exception):
	pass


def _application(*, new: bool, from_date_changed: bool):
	doc = la.LeaveApplication.__new__(la.LeaveApplication)
	doc.__dict__.update(
		{
			"name": "HR-LAP-OLD",
			"employee": "EMP-1",
			"leave_type": "Annual Leave",
			"from_date": date(2026, 9, 10),
			"to_date": date(2026, 9, 10),
			"half_day": 0,
			"half_day_date": None,
			"status": "Approved",
			"docstatus": 0,
		}
	)
	doc.is_new = lambda: new
	doc.has_value_changed = lambda field: from_date_changed
	return doc


class TestBackdatedRestrictionGovernsCreationNotDecision(unittest.TestCase):
	def setUp(self):
		settings = {
			"restrict_backdated_leave_application": 1,
			"role_allowed_to_create_backdated_leave_application": ALLOWED_ROLE,
		}
		approver = frappe._dict(roles=[frappe._dict(role="Employee"), frappe._dict(role="Leave Approver")])
		self.patches = [
			patch.object(frappe, "db", MagicMock()),
			patch.object(frappe, "get_doc", lambda *a, **k: approver),
			patch.object(frappe, "session", frappe._dict(user="approver@example.invalid"), create=True),
			patch.object(
				frappe, "throw", side_effect=lambda msg, *a, **k: (_ for _ in ()).throw(_Refused(msg))
			),
			patch.object(la, "getdate", lambda value=None: TODAY if value is None else value),
			patch.object(la, "is_lwp", lambda leave_type: True),
		]
		for p in self.patches:
			p.start()
		frappe.db.get_single_value.side_effect = lambda doctype, field: settings.get(field)

	def tearDown(self):
		for p in reversed(self.patches):
			p.stop()

	def test_deciding_an_existing_past_dated_application_is_not_a_backdated_creation(self):
		doc = _application(new=False, from_date_changed=False)
		la.LeaveApplication.validate_dates(doc)  # must not raise

	def test_creating_a_backdated_application_still_needs_the_role(self):
		with self.assertRaises(_Refused) as refused:
			la.LeaveApplication.validate_dates(_application(new=True, from_date_changed=True))
		self.assertIn(ALLOWED_ROLE, str(refused.exception))

	def test_moving_an_existing_application_into_the_past_still_needs_the_role(self):
		with self.assertRaises(_Refused):
			la.LeaveApplication.validate_dates(_application(new=False, from_date_changed=True))


if __name__ == "__main__":
	unittest.main()

# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

"""Approver fence (hrms.hr.utils.validate_staff_approver) — filing-for-others branch.

Pure unit tests: `frappe` is mocked, so these run without a bench or site
(same runnable pattern as hrms/tests/test_staff_lockdown_permlevel.py).

What they pin down: a designated approver may act on someone else's SAVED
request, and only because the approver value is the one ALREADY STORED on the
document — never the one arriving in the payload.
"""

import types
import unittest
from unittest.mock import MagicMock, patch

import frappe

from hrms.tests import _erpnext_stub

_erpnext_stub.install()

from hrms.hr import utils as hr_utils

STAFF = "staff@example.com"
MANAGER = "manager@example.com"
FRIEND = "friend@example.com"

STAFF_EMPLOYEE = "HR-EMP-001"

# user_id, leave_approver, reports_to, department of the request's employee
EMPLOYEE_INFO = {
	"user_id": STAFF,
	"leave_approver": MANAGER,
	"reports_to": None,
	"department": None,
}


class _Doc:
	def __init__(self, name, employee, leave_approver, is_new=False):
		self.doctype = "Leave Application"
		self.name = name
		self.employee = employee
		self.leave_approver = leave_approver
		self._is_new = is_new

	def is_new(self):
		return self._is_new

	def get(self, fieldname):
		return getattr(self, fieldname, None)


class _Ctx:
	"""Patch the frappe surface validate_staff_approver touches.

	stored_approver: what the DB holds for the document's leave_approver.
	employee_write: whether the session user has Employee write on doc.employee.
	"""

	def __init__(self, user, stored_approver=None, employee_write=False):
		self.user = user
		self.stored_approver = stored_approver
		self.employee_write = employee_write

	def __enter__(self):
		def get_value(doctype, filters, fieldname=None, **kwargs):
			if doctype == "Employee":
				if kwargs.get("as_dict"):
					return frappe._dict({k: EMPLOYEE_INFO.get(k) for k in fieldname})
				return EMPLOYEE_INFO.get(fieldname)
			if doctype == "Leave Application":
				return self.stored_approver
			return None

		db = MagicMock()
		db.get_value.side_effect = get_value

		local = types.SimpleNamespace()
		local.flags = frappe._dict(in_test=False)

		def throw(msg, exc=frappe.ValidationError, **kwargs):
			raise exc(msg)

		self.patches = [
			# frappe's translator needs a bench log dir; the fence only needs a
			# message string and a throw that raises the right exception class
			patch.object(hr_utils, "_", lambda msg: msg),
			patch.object(frappe, "throw", side_effect=throw),
			patch.object(frappe, "db", db),
			patch.object(frappe, "session", frappe._dict(user=self.user)),
			patch.object(frappe, "local", local),
			patch.object(frappe, "get_roles", side_effect=lambda _u: ["Employee"]),
			patch.object(frappe, "get_all", return_value=[]),
			patch.object(frappe, "has_permission", return_value=self.employee_write),
		]
		for p in self.patches:
			p.start()
		return self

	def __exit__(self, *exc):
		for p in self.patches:
			p.stop()


def _validate(doc):
	hr_utils.validate_staff_approver(doc, "leave_approver", "leave_approver", "leave_approvers")


class TestApproverFenceForOtherEmployees(unittest.TestCase):
	def test_stored_approver_may_act_on_saved_request(self):
		"""The bug: the designated approver submitting someone else's request
		tripped the filing fence."""
		doc = _Doc("HR-LAP-0001", STAFF_EMPLOYEE, MANAGER)
		with _Ctx(MANAGER, stored_approver=MANAGER):
			_validate(doc)  # must not raise

	def test_payload_approver_cannot_unlock_someone_elses_request(self):
		"""Naming yourself approver in the same save must not pass the fence —
		only the DB-stored value counts."""
		doc = _Doc("HR-LAP-0001", STAFF_EMPLOYEE, FRIEND)
		with _Ctx(FRIEND, stored_approver=MANAGER):
			self.assertRaises(frappe.PermissionError, _validate, doc)

	def test_new_doc_for_another_employee_still_blocked(self):
		"""Creating a request for someone else without Employee write is
		unchanged — there is no stored approver to trust yet."""
		doc = _Doc("new-leave-application-1", STAFF_EMPLOYEE, MANAGER, is_new=True)
		with _Ctx(MANAGER, stored_approver=MANAGER):
			self.assertRaises(frappe.PermissionError, _validate, doc)

	def test_employee_write_still_allows_filing_for_others(self):
		doc = _Doc("new-leave-application-1", STAFF_EMPLOYEE, MANAGER, is_new=True)
		with _Ctx("hrassistant@example.com", stored_approver=None, employee_write=True):
			_validate(doc)  # must not raise

	def test_self_approval_check_untouched_for_own_request(self):
		"""The employee is still barred from routing their own request to
		themselves, whatever the stored value says."""
		doc = _Doc("HR-LAP-0001", STAFF_EMPLOYEE, STAFF)
		with _Ctx(STAFF, stored_approver=STAFF):
			self.assertRaises(frappe.ValidationError, _validate, doc)


if __name__ == "__main__":
	unittest.main()

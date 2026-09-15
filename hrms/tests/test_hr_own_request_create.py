"""A company-fenced HR user can file their OWN request before `company` exists.

15 September 2026: an HR User with an Employee record filed a New Attendance
Request in Nadi for themselves and got "You need the 'create' permission on
Attendance Request" — Frappe's DOC-level refusal. The role had create; the
refusal came from `hrms.overrides.employee_owned_row_scope.has_permission`.

For an HR-sight user the hook fences the row on `doc.company`. On a NEW doc
that field is not yet the row's company: `Document.insert` runs
`check_permission("create")` BEFORE `_validate_links()`, which is where the
`fetch_from: employee.company` value is written, and Nadi never sends
`company`. So at check time it is whatever Frappe's user default supplied:

  * an "HR (Instance)" user holds N `allow=Company` User Permissions, so there
    is no single default and `company` is None — `company_visible(None)` is
    False and the HR user is refused their own request (reproduced on
    fresh.local with the exact wording);
  * an "HR (Company)" user gets their fenced company as the default whatever
    employee the request names, so the fence passed a request for an employee
    OUTSIDE the fence and `fetch_from` then wrote that other company in.

An unsaved row is therefore fenced on its EMPLOYEE's company (the value the
save will write) as well as any company it already carries; a saved row keeps
answering with its stored company. Plain-employee scope is untouched.

Bench-free (frappe stubbed):

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_hr_own_request_create.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.overrides import company_scope
from hrms.overrides import employee_owned_row_scope as scope

HR = "hr@example.com"
STAFF = "staff@example.com"
DOCTYPE = "Attendance Request"
EMPLOYEE_COMPANY = {"EMP-HR": "CO-A", "EMP-A": "CO-A", "EMP-B": "CO-B"}


def _employee_company(doctype, name, fieldname=None, *args, **kwargs):
	if doctype == "Employee" and fieldname == "company":
		return EMPLOYEE_COMPANY.get(name)
	raise AssertionError(f"unexpected read {doctype} {name} {fieldname}")


def new_request(employee, company=None):
	"""What `Document.insert` hands the hook: unsaved, unnamed, company as the
	user default left it (None when the user has no single default)."""
	return frappe._dict(doctype=DOCTYPE, name=None, employee=employee, company=company, __islocal=1)


def saved_request(employee, company, name="HR-ARQ-26-09-00001"):
	return frappe._dict(doctype=DOCTYPE, name=name, employee=employee, company=company)


class _Scope(unittest.TestCase):
	def create_allowed(self, doc, user, *, hr, fence, own=()):
		with (
			patch.object(scope, "sees_all_employee_data", return_value=hr),
			patch.object(company_scope, "allowed_companies", return_value=list(fence)),
			patch.object(scope, "own_employees", return_value=list(own)),
			patch.object(scope, "get_direct_report_employees", return_value=[]),
			patch.object(scope, "get_shared", return_value=[]),
			patch.object(frappe.db, "get_value", side_effect=_employee_company),
		):
			return scope.has_permission(doc, "create", user)


class TestHrFilesTheirOwnRequest(_Scope):
	def test_hr_instance_user_passes_with_no_default_company(self):
		"""Two Company UPs -> no single default -> company None at check time."""
		self.assertTrue(
			self.create_allowed(new_request("EMP-HR"), HR, hr=True, fence=["CO-A", "CO-B"]),
			"an HR user fenced to CO-A and CO-B must be able to file for their own CO-A employee",
		)

	def test_hr_company_fenced_user_passes_with_no_default_company(self):
		self.assertTrue(self.create_allowed(new_request("EMP-HR"), HR, hr=True, fence=["CO-A"]))

	def test_hr_company_fenced_user_passes_when_the_default_is_their_company(self):
		self.assertTrue(
			self.create_allowed(new_request("EMP-HR", company="CO-A"), HR, hr=True, fence=["CO-A"])
		)

	def test_group_hr_is_unfenced(self):
		self.assertTrue(self.create_allowed(new_request("EMP-HR"), HR, hr=True, fence=[]))


class TestTheFenceStillHolds(_Scope):
	def test_fenced_hr_cannot_file_for_an_employee_outside_the_fence(self):
		"""The user default fills company=CO-A; the employee is in CO-B, and that
		is the company the save will write. Refused."""
		self.assertFalse(
			self.create_allowed(new_request("EMP-B", company="CO-A"), HR, hr=True, fence=["CO-A"]),
			"a CO-A-fenced HR user must not create a CO-B employee's request",
		)

	def test_fenced_hr_with_no_employee_on_the_row_is_refused(self):
		self.assertFalse(self.create_allowed(new_request(None), HR, hr=True, fence=["CO-A"]))

	def test_saved_row_is_fenced_on_its_stored_company(self):
		"""A saved row's company is authoritative; the employee is not re-read."""
		with patch.object(frappe.db, "get_value", side_effect=AssertionError("must not read Employee")):
			with (
				patch.object(scope, "sees_all_employee_data", return_value=True),
				patch.object(company_scope, "allowed_companies", return_value=["CO-A"]),
			):
				self.assertTrue(scope.has_permission(saved_request("EMP-B", "CO-A"), "read", HR))
				self.assertFalse(scope.has_permission(saved_request("EMP-A", "CO-B"), "read", HR))

	def test_employee_filing_for_a_colleague_is_refused_as_before(self):
		self.assertFalse(self.create_allowed(new_request("EMP-A"), STAFF, hr=False, fence=[], own=["EMP-B"]))

	def test_employee_filing_for_themselves_passes_as_before(self):
		self.assertTrue(self.create_allowed(new_request("EMP-A"), STAFF, hr=False, fence=[], own=["EMP-A"]))


if __name__ == "__main__":
	unittest.main()

"""Request Access Health — the report lists refusals, fenced, HR-only.

Two users linked to Active Employees, one of them refused: the report shows
one row, naming the gate and the plain sentence. The company fence reaches
the walk; an empty fence is "everyone"; a doctype filter narrows the walk to
that one doctype. The JSON grants HR Manager and System Manager only — no
staff role, so test_report_role_integrity never sees a self-scope question.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_request_access_health.py
"""

import json
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr.report.request_access_health import request_access_health as report
from hrms.utils import request_access as ra

HERE = pathlib.Path(__file__).resolve()
REPORT_DIR = HERE.parents[1] / "hr" / "report" / "request_access_health"


class TestTheReport(unittest.TestCase):
	def _execute(self, filters=None, fence=None, people=None, allowed=None):
		people = people or [
			frappe._dict(
				user="ann@example.com", employee="E1", employee_name="Ann", company="Co A", ambiguous=[]
			),
			frappe._dict(
				user="bob@example.com", employee="E2", employee_name="Bob", company="Co A", ambiguous=[]
			),
		]
		allowed = allowed or (lambda user, dt: user != "bob@example.com")
		local = frappe._dict(session=frappe._dict(user="hr@example.com", sid="s", data={}), form_dict={})
		with (
			patch.object(report, "fenced_companies", return_value=list(fence or [])) as fenced,
			patch.object(ra, "linked_users", return_value=people) as linked,
			patch.object(
				ra, "create_allowed", side_effect=lambda dt, user, employee, meta=None: allowed(user, dt)
			),
			patch.object(
				ra,
				"diagnose_for_user",
				side_effect=lambda dt, user, employee=None: {
					"refused_by": "hrms.overrides.employee_issue_row_scope.has_permission",
					"why": "the hook refused",
				},
			),
			patch.object(frappe, "local", local),
			patch.object(frappe, "set_user"),
			patch.object(frappe, "get_meta"),
		):
			columns, rows = report.execute(filters)
		return columns, rows, fenced, linked

	def test_two_users_one_refused_is_one_row_per_refused_doctype(self):
		columns, rows, _, _ = self._execute()
		self.assertEqual({r["user"] for r in rows}, {"bob@example.com"})
		self.assertEqual(len(rows), len(ra.PWA_REQUEST_DOCTYPES))
		self.assertEqual(rows[0]["employee_name"], "Bob")
		self.assertEqual(rows[0]["refused_by"], "hrms.overrides.employee_issue_row_scope.has_permission")
		self.assertEqual(rows[0]["why"], "the hook refused")
		self.assertEqual(
			[c["fieldname"] for c in columns],
			["user", "employee", "employee_name", "company", "doctype", "refused_by", "why"],
		)

	def test_everyone_allowed_is_an_empty_report(self):
		_, rows, _, _ = self._execute(allowed=lambda user, dt: True)
		self.assertEqual(rows, [])

	def test_the_company_fence_reaches_the_walk(self):
		_, _, fenced, linked = self._execute({"company": "Co A"}, fence=["Co A"])
		fenced.assert_called_once_with("Co A")
		linked.assert_called_once_with(["Co A"])

	def test_no_fence_means_everyone(self):
		_, _, _, linked = self._execute({})
		linked.assert_called_once_with(None)

	def test_the_doctype_filter_narrows_the_walk(self):
		_, rows, _, _ = self._execute({"doctype": "Employee Issue"})
		self.assertEqual([r["doctype"] for r in rows], ["Employee Issue"])


class TestTheReportDefinition(unittest.TestCase):
	def setUp(self):
		self.meta = json.loads((REPORT_DIR / "request_access_health.json").read_text())

	def test_hr_manager_and_system_manager_only(self):
		self.assertEqual({r["role"] for r in self.meta["roles"]}, {"HR Manager", "System Manager"})

	def test_is_a_standard_script_report_over_employee(self):
		self.assertEqual(self.meta["report_type"], "Script Report")
		self.assertEqual(self.meta["is_standard"], "Yes")
		self.assertEqual(self.meta["ref_doctype"], "Employee")
		self.assertEqual(self.meta["name"], "Request Access Health")

	def test_the_js_filter_options_are_the_matrix(self):
		js = (REPORT_DIR / "request_access_health.js").read_text()
		for doctype in ra.PWA_REQUEST_DOCTYPES:
			self.assertIn(f'"{doctype}"', js, doctype)
		for doctype in ra.NOT_SELF_SERVICE:
			self.assertNotIn(f'"{doctype}"', js, f"{doctype} is not self-service by design")


if __name__ == "__main__":
	unittest.main()

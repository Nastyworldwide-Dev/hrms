"""A request's company is the Employee's company, whatever the form sent.

PYTHONPATH=. python3 hrms/overrides/test_employee_company_default.py
"""

import ast
import json
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _frappe_stub

_frappe_stub.install()

import frappe

from hrms.overrides.employee_company_default import set_company_from_employee

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHIFT_REQUEST = ROOT / "hr" / "doctype" / "shift_request" / "shift_request.py"

# Every request doctype the PWA creates through FormView -> frappe.client.insert
# without sending a company. Each must get it from the Employee server-side.
PWA_REQUEST_DOCTYPES = (
	"shift_request",
	"attendance_request",
	"leave_application",
	"ot_request",
	"replacement_leave_claim",
	"employee_issue",
	"expense_claim",
	"shift_assignment",
	"employee_advance",
	"travel_request",
	"shift_swap_request",
	"compensatory_leave_request",
)


class TestSetCompanyFromEmployee(unittest.TestCase):
	def _run(self, doc, employee_company="Nostalgya"):
		with patch.object(frappe.db, "get_value", return_value=employee_company) as get_value:
			set_company_from_employee(doc)
		return get_value

	def test_empty_company_is_filled_from_the_employee(self):
		doc = frappe._dict(doctype="Shift Request", employee="HR-EMP-00014", company=None)
		get_value = self._run(doc)
		self.assertEqual(doc.company, "Nostalgya")
		get_value.assert_called_once_with("Employee", "HR-EMP-00014", "company")

	def test_client_company_never_wins(self):
		doc = frappe._dict(doctype="Shift Request", employee="HR-EMP-00014", company="Other Co")
		self._run(doc)
		self.assertEqual(doc.company, "Nostalgya")

	def test_no_employee_leaves_the_doc_alone(self):
		doc = frappe._dict(doctype="Shift Request", employee=None, company="")
		get_value = self._run(doc)
		self.assertEqual(doc.company, "")
		get_value.assert_not_called()

	def test_employee_without_company_is_left_for_the_mandatory_check(self):
		doc = frappe._dict(doctype="Shift Request", employee="HR-EMP-00014", company="")
		self._run(doc, employee_company=None)
		self.assertEqual(doc.company, "")


class TestWiring(unittest.TestCase):
	def test_shift_request_validate_sets_company_first(self):
		"""validate() derives company before any rule that reads it."""
		tree = ast.parse(SHIFT_REQUEST.read_text())
		validate = next(
			node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "validate"
		)
		first = validate.body[0]
		call = getattr(first, "value", None)
		self.assertIsInstance(call, ast.Call, "validate() must start with a call")
		self.assertEqual(ast.unparse(call), "set_company_from_employee(self)")

	def test_every_pwa_request_doctype_gets_company_from_the_employee(self):
		"""Invariant: a required company on a PWA-created request is never the client's job.

		Either the DocType JSON fetches it from the employee, or the controller
		calls the shared helper. A doctype with no required company is out of scope.
		"""
		unguarded = []
		for dt in PWA_REQUEST_DOCTYPES:
			folder = ROOT / "hr" / "doctype" / dt
			meta = json.loads((folder / f"{dt}.json").read_text())
			company = next((f for f in meta["fields"] if f["fieldname"] == "company"), None)
			if not company or not company.get("reqd"):
				continue
			if company.get("fetch_from", "").endswith(".company"):
				continue
			if "set_company_from_employee(self)" in (folder / f"{dt}.py").read_text():
				continue
			unguarded.append(dt)
		self.assertEqual(unguarded, [])


if __name__ == "__main__":
	unittest.main()

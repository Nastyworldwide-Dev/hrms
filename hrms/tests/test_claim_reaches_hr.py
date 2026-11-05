"""A claim reaches HR: straight away when nobody is above the employee, and with a
notice when the manager approves (owner, 5 Nov 2026).

    PYTHONPATH=.:hrms/tests python3 -m pytest -q -p no:cacheprovider hrms/tests/test_claim_reaches_hr.py
"""

import ast
import pathlib
import unittest
import unittest.mock
from types import SimpleNamespace
from unittest.mock import MagicMock

SOURCE = pathlib.Path(__file__).resolve().parents[1] / "hr" / "doctype" / "expense_claim" / "expense_claim.py"


def _method(name, ns):
	tree = ast.parse(SOURCE.read_text())
	cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ExpenseClaim")
	fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SOURCE), "exec"), ns)
	return ns[name]


class TestAClaimWithNobodyAboveGoesToHR(unittest.TestCase):
	def start(self, has_manager, status="Draft", workflow=None):
		ns = {
			"frappe": MagicMock(),
			"logger": MagicMock(),
			"has_approver_above": lambda employee, doctype: has_manager,
			"get_workflow_name": lambda dt: workflow,
			"claim_stages": __import__("hrms.utils.claim_stages", fromlist=["x"]),
		}
		doc = SimpleNamespace(employee="HR-EMP-1", approval_status=status, name=None)
		_method("start_at_the_right_step", ns)(doc)
		return doc.approval_status

	def test_with_a_manager_it_waits_for_them(self):
		self.assertEqual(self.start(True), "Draft")

	def test_with_nobody_above_it_waits_for_hr(self):
		self.assertEqual(self.start(False), "Waiting for HR")

	def test_a_claim_filed_already_decided_is_left_alone(self):
		self.assertEqual(self.start(False, status="Approved"), "Approved")

	def test_a_site_with_a_workflow_is_left_alone(self):
		self.assertEqual(self.start(False, workflow="Claims"), "Draft")


class TestHRIsToldWhenAClaimReachesThem(unittest.TestCase):
	def notify(self, hr_users, employee_user="staff@x.com"):
		inserted = []
		frappe = MagicMock()
		frappe.new_doc.side_effect = lambda dt: SimpleNamespace(insert=lambda **kw: inserted.append(1))
		ns = {
			"frappe": frappe,
			"logger": MagicMock(),
			"bold": lambda s: s,
			"_claim_hr_users": lambda doc: hr_users,
		}
		doc = SimpleNamespace(
			name="HR-EXP-1",
			doctype="Expense Claim",
			employee_name="Siti",
			_get_employee_user=lambda: employee_user,
		)
		sent = _method("notify_hr_step", ns)(doc)
		return sent, len(inserted)

	def test_every_hr_person_who_can_act_is_told(self):
		self.assertEqual(self.notify(["hr1@x.com", "hr2@x.com"]), (["hr1@x.com", "hr2@x.com"], 2))

	def test_an_hr_claimant_is_not_told_about_their_own_claim(self):
		sent, _n = self.notify(["hr1@x.com", "staff@x.com"])
		self.assertEqual(sent, ["hr1@x.com"])


class TestHRMayDecideTheirOwnClaimAtTheHRStep(unittest.TestCase):
	"""Owner: "their reporting manager than any hr including themselve". The Desk self
	check runs before submit; it must let the HR step through for an HR claimant, and
	only the HR step, and only when decide() vouched for it."""

	def check(self, status, *, hr_step_flag, prevent=True, above=True):
		frappe = MagicMock()
		frappe.throw.side_effect = RuntimeError
		frappe.db.get_single_value.return_value = prevent
		ns = {"frappe": frappe, "_": lambda s: s, "get_workflow_name": lambda dt: None, "logger": MagicMock()}
		import sys

		hr_utils = MagicMock()
		hr_utils.is_own_employee = lambda e: True
		hr_utils.has_approver_above = lambda e, dt: above
		ns["claim_stages"] = __import__("hrms.utils.claim_stages", fromlist=["x"])
		fn = _method("validate_for_self_approval", ns)
		doc = SimpleNamespace(
			name="HR-EXP-9",
			employee="HR-EMP-HR",
			approval_status=status,
			flags={"hr_step_decision": hr_step_flag},
		)
		with unittest.mock.patch.dict(sys.modules, {"hrms.hr.utils": hr_utils}):
			fn(doc)

	def test_hr_approving_their_own_claim_at_the_hr_step_is_allowed(self):
		self.check("Approved", hr_step_flag=True)

	def test_without_decides_say_so_it_is_still_refused(self):
		with self.assertRaises(RuntimeError):
			self.check("Approved", hr_step_flag=False)


if __name__ == "__main__":
	unittest.main()

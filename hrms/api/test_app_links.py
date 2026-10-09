"""Which sibling apps a person is offered is the server's answer (audit F-15:
no role names in the frontend). The PWA gets app KEYS; the role rule lives
here, next to the roles it reads.

    PYTHONPATH=. python3 -m pytest -q hrms/api/test_app_links.py
"""

import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.api import app_links


class TestMyApps(unittest.TestCase):
	def _apps(self, roles):
		with (
			patch.object(frappe, "get_roles", return_value=roles, create=True),
			patch.object(frappe, "session", frappe._dict(user="x@example.com")),
		):
			return app_links.get_my_apps()

	def test_every_employee_is_offered_approva_and_not_the_board(self):
		# Owner, 9 Oct 2026: everyone can open Approva (and send a request), so
		# the baseline Employee role is enough. The board stays role-gated.
		self.assertEqual(self._apps(["Employee"]), ["approva"])

	def test_someone_with_no_role_here_is_offered_nothing(self):
		self.assertEqual(self._apps(["Guest"]), [])

	def test_finance_gets_approva_only(self):
		self.assertEqual(self._apps(["Employee", "Accounts User"]), ["approva"])

	def test_approva_user_gets_approva_and_nothing_else(self):
		# Owner, 30 Sep 2026: a special-case role for someone who needs Approva
		# without the accounting or HR access the other roles carry.
		self.assertEqual(self._apps(["Employee", "Approva User"]), ["approva"])

	def test_the_roles_that_already_had_approva_keep_it(self):
		for role in ("Accounts Manager", "Accounts User", "System Manager", "HR Manager", "HR User"):
			self.assertIn("approva", self._apps([role]), role)

	def test_projects_gets_the_board_only(self):
		self.assertEqual(self._apps(["Projects User"]), ["board"])

	def test_hr_manager_gets_both_in_a_fixed_order(self):
		self.assertEqual(self._apps(["HR Manager"]), ["approva", "board"])

	def test_the_caller_is_never_a_parameter(self):
		import inspect

		self.assertEqual(list(inspect.signature(app_links.get_my_apps).parameters), [])

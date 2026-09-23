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

	def test_an_employee_is_offered_no_app(self):
		self.assertEqual(self._apps(["Employee"]), [])

	def test_finance_gets_approva_only(self):
		self.assertEqual(self._apps(["Employee", "Accounts User"]), ["approva"])

	def test_projects_gets_the_board_only(self):
		self.assertEqual(self._apps(["Projects User"]), ["board"])

	def test_hr_manager_gets_both_in_a_fixed_order(self):
		self.assertEqual(self._apps(["HR Manager"]), ["approva", "board"])

	def test_the_caller_is_never_a_parameter(self):
		import inspect

		self.assertEqual(list(inspect.signature(app_links.get_my_apps).parameters), [])

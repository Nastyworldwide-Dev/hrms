"""hrms.api.helpdesk — the PWA's native Helpdesk front end.

Pins the two things the PWA relies on and cannot see for itself:

* a ticket list row always carries `raised_by_name` (the employee behind the
  raising user, falling back to the raw email) — the HR request was "show
  who raised the ticket in the HRM";
* availability is a plain installed-apps check, so a site without the
  Helpdesk app hides the section instead of erroring on every open.

    PYTHONPATH=. python3 hrms/tests/test_helpdesk_api.py
"""

import importlib.util
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

import frappe

# Loaded by path so hrms.api.__init__ (which drags in half the app) stays out
MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "api" / "helpdesk.py"
_spec = importlib.util.spec_from_file_location("hrms_api_helpdesk", MODULE_PATH)
helpdesk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helpdesk)


class TestRaiserName(unittest.TestCase):
	def test_rows_get_employee_name_or_email_fallback(self):
		rows = [
			{"name": "HD-1", "raised_by": "amy@x.com"},
			{"name": "HD-2", "raised_by": "ghost@x.com"},
			{"name": "HD-3", "raised_by": None},
		]
		with patch.object(
			frappe, "get_all", return_value=[{"user_id": "amy@x.com", "employee_name": "Amy E."}]
		):
			out = helpdesk._attach_raiser_names(rows)
		self.assertEqual([r["raised_by_name"] for r in out], ["Amy E.", "ghost@x.com", ""])

	def test_no_rows_means_no_employee_query(self):
		with patch.object(frappe, "get_all") as get_all:
			self.assertEqual(helpdesk._attach_raiser_names([]), [])
			get_all.assert_not_called()


class TestAvailability(unittest.TestCase):
	def test_available_only_when_app_installed(self):
		with patch.object(frappe, "get_installed_apps", return_value=["frappe", "hrms"]):
			self.assertFalse(helpdesk.is_available())
		with patch.object(frappe, "get_installed_apps", return_value=["frappe", "helpdesk", "hrms"]):
			self.assertTrue(helpdesk.is_available())


class TestNewTicketGuard(unittest.TestCase):
	def test_blank_subject_or_description_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			helpdesk.new_ticket(subject="  ", description="x")
		with self.assertRaises(frappe.ValidationError):
			helpdesk.new_ticket(subject="x", description="")


if __name__ == "__main__":
	unittest.main()

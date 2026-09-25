"""Nobody chooses their approver (owner, 25 Sep 2026: "never to the director
to approve, only their own approver; nobody is supposed to choose").

Staff filing their own request got a picker of everyone up their chain, and
the server accepted any of them. Now, for the employee's own request, the
server SETS the approver to their own (the first rung of the chain HR
configured) whatever was sent. HR / Desk users are not the applicant and keep
their behaviour. Pure: frappe is mocked.
    PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_own_approver_is_set_not_chosen.py
"""

import unittest
from unittest.mock import patch

from hrms.tests import _erpnext_stub

_erpnext_stub.install()

import frappe

from hrms.hr import utils as hr_utils

STAFF, MANAGER, DIRECTOR = "staff@x", "manager@x", "director@x"


class _Doc:
	def __init__(self, **kw):
		self.__dict__.update(kw)

	def is_new(self):
		return True

	def get(self, key):
		return getattr(self, key, None)


def run(sent, chain, user=STAFF, roles=()):
	doc = _Doc(doctype="Leave Application", name="LA-1", employee="E1", leave_approver=sent)
	info = frappe._dict(user_id=STAFF, leave_approver=MANAGER, reports_to=None, department=None)
	with (
		patch.object(frappe, "session", frappe._dict(user=user)),
		patch.object(frappe, "get_roles", return_value=list(roles)),
		patch.object(
			frappe.db, "get_value", side_effect=lambda *a, **k: info if k.get("as_dict") else info.user_id
		),
		patch.object(hr_utils, "get_designated_approvers", return_value=chain),
	):
		hr_utils.validate_staff_approver(doc, "leave_approver", "leave_approver", "leave_approvers")
	return doc.leave_approver


class TestOwnApprover(unittest.TestCase):
	def test_the_director_sent_by_staff_becomes_their_own_approver(self):
		self.assertEqual(run(DIRECTOR, [MANAGER, DIRECTOR]), MANAGER)

	def test_nothing_sent_is_filled_with_their_own_approver(self):
		self.assertEqual(run("", [MANAGER, DIRECTOR]), MANAGER)

	def test_their_own_approver_stays(self):
		self.assertEqual(run(MANAGER, [MANAGER, DIRECTOR]), MANAGER)

	def test_hr_filing_is_untouched(self):
		self.assertEqual(run(DIRECTOR, [MANAGER, DIRECTOR], user="hr@x", roles=["HR Manager"]), DIRECTOR)

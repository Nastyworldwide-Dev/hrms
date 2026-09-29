"""Who may approve: the employee's own line, two levels deep, never someone who
has left (owner, 29 Sep 2026, alpha.20 plan A).

"they can act on behalf, not restraining. as long as they dont reach to even
higher." Level 1 is the employee's approver (the approver named on their
record, and their reporting manager); level 2 is those people's approvers.
Nobody higher. HR can always act (not tested here: HR is admitted before the
chain is read). The number of levels is an HR Setting, default 2.

An approver whose Employee record is no longer Active, or whose login is
disabled, is skipped: the next person moves up, so a request never waits on
someone who has gone.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_approval_chain_two_levels.py
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
from test_approver_chain_follows_each_employee import ORG, _Org

import frappe

from hrms.hr import utils as hr_utils

FIELD, PARENT = "leave_approver", "leave_approvers"

#: You (IT) -> Senior -> Operations Director -> CEO, the owner's example.
LINE = {
	"HR-EMP-YOU": {
		"user_id": "you@x",
		"leave_approver": None,
		"reports_to": "HR-EMP-SENIOR",
		"status": "Active",
	},
	"HR-EMP-SENIOR": {
		"user_id": "senior@x",
		"leave_approver": None,
		"reports_to": "HR-EMP-DIR",
		"status": "Active",
	},
	"HR-EMP-DIR": {
		"user_id": "director@x",
		"leave_approver": None,
		"reports_to": "HR-EMP-CEO",
		"status": "Active",
	},
	"HR-EMP-CEO": {"user_id": "ceo@x", "leave_approver": None, "reports_to": None, "status": "Active"},
	# a named approver who is NOT the reporting manager: both are level 1
	"HR-EMP-NAMEDTOO": {
		"user_id": "n@x",
		"leave_approver": "director@x",
		"reports_to": "HR-EMP-SENIOR",
		"status": "Active",
	},
}
DISABLED_USERS = set()


def run(fn, *args, levels=2):
	with patch.dict(ORG, {**{k: {**v, "department": "IT"} for k, v in LINE.items()}}):
		with _Org():
			db_get = frappe.db.get_value.side_effect

			def get_value(doctype, filters, fieldname=None, **kw):
				if doctype == "User" and fieldname == "enabled":
					return 0 if filters in DISABLED_USERS else 1
				if doctype == "Employee" and fieldname == "status" and isinstance(filters, dict):
					return None
				return db_get(doctype, filters, fieldname, **kw)

			frappe.db.get_value.side_effect = get_value
			with patch.object(hr_utils, "approval_levels", return_value=levels):
				return fn(*args)


def chain(employee, levels=2):
	return run(hr_utils.get_designated_approvers, employee, FIELD, PARENT, levels=levels)


def routed(user, levels=2):
	return sorted(run(hr_utils.get_employees_routed_to, user, FIELD, PARENT, levels=levels))


class TestTwoLevels(unittest.TestCase):
	def test_your_senior_and_the_director_may_approve(self):
		self.assertEqual(chain("HR-EMP-YOU"), ["senior@x", "director@x"])

	def test_the_ceo_does_not(self):
		self.assertNotIn("ceo@x", chain("HR-EMP-YOU"))

	def test_the_ceo_still_approves_the_people_right_under_him(self):
		self.assertEqual(chain("HR-EMP-DIR"), ["ceo@x"])

	def test_hr_can_raise_the_number_of_levels(self):
		self.assertEqual(chain("HR-EMP-YOU", levels=3), ["senior@x", "director@x", "ceo@x"])

	def test_a_named_approver_and_the_manager_are_both_level_one(self):
		# NAMEDTOO names the director AND reports to the senior: both are level
		# 1; level 2 is the senior's approver (the director, already in) and the
		# director's approver (the CEO).
		self.assertEqual(chain("HR-EMP-NAMEDTOO"), ["director@x", "senior@x", "ceo@x"])


class TestTheInverseHasTheSameLimit(unittest.TestCase):
	"""Who sees a request is exactly who may approve it."""

	def test_the_ceo_does_not_see_your_request(self):
		self.assertNotIn("HR-EMP-YOU", routed("ceo@x"))

	def test_the_director_sees_two_levels_down(self):
		self.assertIn("HR-EMP-YOU", routed("director@x"))

	def test_the_two_directions_agree(self):
		for employee in LINE:
			for approver in chain(employee):
				self.assertIn(employee, routed(approver), f"{approver} approves {employee} but can't see it")


class TestPeopleWhoHaveLeft(unittest.TestCase):
	def test_a_departed_senior_is_skipped_and_the_next_moves_up(self):
		with patch.dict(LINE["HR-EMP-SENIOR"], {"status": "Left"}):
			self.assertEqual(chain("HR-EMP-YOU"), ["director@x", "ceo@x"])

	def test_whoever_moves_up_can_also_see_the_request(self):
		# the CEO moves up to level 2 when the senior has left; he must be able
		# to SEE the request too, or Approve is offered on a request he can't open
		with patch.dict(LINE["HR-EMP-SENIOR"], {"status": "Left"}):
			self.assertIn("ceo@x", chain("HR-EMP-YOU"))
			self.assertIn("HR-EMP-YOU", routed("ceo@x"))

	def test_a_disabled_login_is_skipped(self):
		DISABLED_USERS.add("senior@x")
		try:
			self.assertEqual(chain("HR-EMP-YOU"), ["director@x", "ceo@x"])
		finally:
			DISABLED_USERS.discard("senior@x")


if __name__ == "__main__":
	unittest.main()


class TestHrSetsTheLevels(unittest.TestCase):
	"""'dont hardcode, respect the configuration set from hr (desk)' (21 Sep
	2026). The number of levels is an HR Setting that reaches live sites."""

	def test_the_setting_is_defined_with_a_default_of_two(self):
		import ast

		source = (Path(__file__).resolve().parents[1] / "setup.py").read_text()
		self.assertIn('"fieldname": "approval_levels"', source)
		field = source[source.index('"fieldname": "approval_levels"') - 300 :][:700]
		self.assertIn('"default": "2"', field)
		self.assertIn('"fieldtype": "Int"', field)
		ast.parse(source)

	def test_it_reaches_live_sites_through_the_sync_patch(self):
		patches = (Path(__file__).resolve().parents[1] / "patches.txt").read_text()
		self.assertIn("sync_custom_fields_with_code #2026-09-29", patches)

	def test_blank_or_zero_means_the_default(self):
		for raw in (None, "", "0", 0, "junk"):
			with (
				self.subTest(raw=raw),
				patch.object(frappe.db, "sql", return_value=((raw,),) if raw is not None else ()),
			):
				self.assertEqual(hr_utils.approval_levels(), 2)

	def test_hr_can_set_three(self):
		with patch.object(frappe.db, "sql", return_value=(("3",),)):
			self.assertEqual(hr_utils.approval_levels(), 3)

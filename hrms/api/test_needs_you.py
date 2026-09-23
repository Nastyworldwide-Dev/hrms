# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Everything waiting on an approver, counted once and correctly.

The block this feeds shipped in 2.0 rendering ONE row type, because this
module did not exist. What is tested here is the two ways a unified count goes
wrong: counting something that is not routed to the caller (a leak), and
failing to count something that is (a queue somebody never works).
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api.approval import DECIDE_THEN_SUBMIT
from hrms.api.needs_you import ROW_COPY, SCAN_CAP, get_needs_you
from hrms.tests.test_utils import create_company


class TestNeedsYouCopy(FrappeTestCase):
	"""No site state: these are about the map itself."""

	def test_every_approvable_type_has_copy_and_a_route(self):
		"""A type missing from the map is a type that silently stops being
		counted, and the approver is told a total that is short."""
		missing = [doctype for doctype in DECIDE_THEN_SUBMIT if doctype not in ROW_COPY]
		self.assertEqual(missing, [], "every approvable type needs a word and a destination")

	def test_no_row_says_a_doctype_name(self):
		""""Attendance Request" is a table. "attendance fix" is what somebody is
		actually waiting for."""
		for doctype, (noun, _nouns, _route) in ROW_COPY.items():
			self.assertNotEqual(noun, doctype.lower())
			self.assertNotIn("request" if doctype.endswith("Request") else "@@", noun.title())

	def test_the_type_list_is_not_a_second_copy(self):
		"""It iterates DECIDE_THEN_SUBMIT rather than keeping its own list —
		two lists of "what is approvable" would drift, and the drift would be a
		type nobody is told about."""
		import inspect

		from hrms.api import needs_you

		source = inspect.getsource(needs_you.get_needs_you)
		self.assertIn("DECIDE_THEN_SUBMIT.items()", source)


class TestNeedsYou(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Leave Application")
		frappe.db.delete("Attendance Request")

		self.company = create_company("_Test Needs You").name
		self.boss_user = "needs_you_boss@example.com"
		self.staff_user = "needs_you_staff@example.com"
		self.bystander_user = "needs_you_other@example.com"
		self.boss = make_employee(self.boss_user, company=self.company)
		self.staff = make_employee(self.staff_user, company=self.company)
		self.bystander = make_employee(self.bystander_user, company=self.company)
		frappe.db.set_value(
			"Employee",
			self.staff,
			{"reports_to": self.boss, "leave_approver": self.boss_user},
		)
		self.leave_type = frappe.db.get_value("Leave Type", {}, "name")

	def tearDown(self):
		frappe.set_user("Administrator")

	def _attendance_request(self, employee=None):
		return frappe.get_doc(
			{
				"doctype": "Attendance Request",
				"employee": employee or self.staff,
				"from_date": add_days(nowdate(), -3),
				"to_date": add_days(nowdate(), -3),
				"reason": "On Duty",
				"company": self.company,
			}
		).insert(ignore_permissions=True)

	def test_the_approver_is_told_what_is_waiting(self):
		self._attendance_request()
		frappe.set_user(self.boss_user)
		out = get_needs_you()
		self.assertEqual(out["total"], 1)
		self.assertEqual(out["rows"][0]["doctype"], "Attendance Request")
		self.assertEqual(out["rows"][0]["noun"], "attendance fix")

	def test_a_bystander_is_told_nothing(self):
		"""The leak that matters: a colleague must not see a queue routed to
		somebody else."""
		self._attendance_request()
		frappe.set_user(self.bystander_user)
		self.assertEqual(get_needs_you()["total"], 0)

	def test_the_requester_does_not_see_their_own_request_as_work(self):
		"""You can read your own request and must never be able to decide it —
		so it is not waiting ON you, and counting it would put a row on Home
		that does nothing when tapped."""
		self._attendance_request()
		frappe.set_user(self.staff_user)
		self.assertEqual(get_needs_you()["total"], 0)

	def test_a_decided_request_stops_counting(self):
		"""Pending means the field says so AND it is unsubmitted: `approval`
		treats docstatus 1 as decided whatever the field says, because that is
		when the consequence lands."""
		doc = self._attendance_request()
		frappe.set_user(self.boss_user)
		self.assertEqual(get_needs_you()["total"], 1)
		frappe.set_user("Administrator")
		frappe.db.set_value("Attendance Request", doc.name, "docstatus", 1)
		frappe.set_user(self.boss_user)
		self.assertEqual(get_needs_you()["total"], 0)

	def test_two_kinds_are_two_rows_with_one_total(self):
		"""The whole slice: before this, an approver with two kinds of work
		waiting saw at most one of them."""
		self._attendance_request()
		frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": self.staff,
				"leave_type": self.leave_type,
				"from_date": add_days(nowdate(), 10),
				"to_date": add_days(nowdate(), 10),
				"status": "Open",
				"leave_approver": self.boss_user,
				"company": self.company,
			}
		).insert(ignore_permissions=True)
		frappe.set_user(self.boss_user)
		out = get_needs_you()
		self.assertEqual(len(out["rows"]), 2)
		self.assertEqual(out["total"], 2)

	def test_a_big_queue_is_capped_and_says_so(self):
		"""The scan is bounded so Home's first paint does not wait on thousands
		of per-document permission checks. Past the cap the block says "20+",
		which is the same decision an approver makes anyway."""
		for _ in range(SCAN_CAP + 2):
			self._attendance_request()
		frappe.set_user(self.boss_user)
		row = get_needs_you()["rows"][0]
		self.assertEqual(row["count"], SCAN_CAP)
		self.assertTrue(row["capped"], "a capped count must not be reported as exact")

	def test_nothing_waiting_is_an_empty_list(self):
		frappe.set_user(self.boss_user)
		out = get_needs_you()
		self.assertEqual(out["rows"], [])
		self.assertEqual(out["total"], 0)

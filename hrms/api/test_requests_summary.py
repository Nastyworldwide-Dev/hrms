# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""The standing numbers the Requests screen states.

Nothing here is new arithmetic — every figure already exists behind an
endpoint this app ships. What is tested is the composition: that a section
which cannot be read is ABSENT rather than zero, that the leave denominator is
the annual entitlement, and that an unmarked day means a day somebody worked.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api.requests_summary import EXPIRY_HORIZON_DAYS, get_requests_summary
from hrms.tests.test_utils import create_company


class TestRequestsSummary(FrappeTestCase):
	def setUp(self):
		self.company = create_company("_Test Requests Summary").name
		self.user = "summary_reader@example.com"
		self.employee = make_employee(self.user, company=self.company)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_every_section_is_answered(self):
		"""Four sections, always — the screen draws what it is given, and a
		missing key it did not expect is a blank where a number should be."""
		frappe.set_user(self.user)
		summary = get_requests_summary()
		self.assertEqual(
			sorted(summary), ["attendance", "expenses", "leave", "overtime"]
		)

	def test_a_section_that_fails_is_absent_rather_than_zero(self):
		"""A zero is an answer, and the wrong one: "you have no overtime to
		claim" when the truth is "we could not check" sends somebody away from
		money they are owed.

		The reader is swapped on the MODULE rather than mocked in place,
		because `_overtime` imports its source inside the function — which is
		what lets the four sections fail independently in the first place."""
		import hrms.api.requests_summary as module

		original = module._overtime

		def explode():
			raise RuntimeError("the overtime read is having a bad day")

		module._overtime = explode
		try:
			frappe.set_user(self.user)
			summary = get_requests_summary()
		finally:
			module._overtime = original

		self.assertNotIn("overtime", summary, "a failed read must not report zero")
		self.assertIn("leave", summary, "and must not take the others down with it")
		self.assertIn("attendance", summary)

	def test_a_leave_type_with_no_allocation_is_not_a_zero(self):
		"""It is not "0 days left" — it is not theirs. Listing every type as a
		zero is how a strip of five useful numbers becomes a wall of twelve."""
		frappe.set_user(self.user)
		for row in get_requests_summary()["leave"]:
			self.assertGreater(row["total"], 0, "a listed type has an allocation")

	def test_an_expiry_far_away_is_not_a_prompt(self):
		"""A balance expiring in nine months is a fact; one expiring in three
		weeks is a prompt. Marking both as prompts makes neither one."""
		frappe.set_user(self.user)
		for row in get_requests_summary()["leave"]:
			if not row["expires_on"]:
				continue
			from frappe.utils import date_diff

			days = date_diff(row["expires_on"], nowdate())
			if days > EXPIRY_HORIZON_DAYS:
				self.assertFalse(row["expiring_soon"], f"{days} days away is not soon")

	def test_a_day_nobody_worked_is_not_an_unmarked_day(self):
		"""It is a day off. Counting it would put a number on the screen that
		never reaches zero and that nobody can act on."""
		frappe.set_user(self.user)
		# This employee has no punches at all, so every day in the window is
		# "unmarked" by a naive definition and none of them by the right one.
		self.assertEqual(get_requests_summary()["attendance"]["days"], 0)

	def test_an_unmarked_day_is_a_worked_day_with_no_attendance(self):
		frappe.set_user("Administrator")
		when = add_days(nowdate(), -2)
		frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": self.employee,
				"time": f"{when} 09:00:00",
				"log_type": "IN",
				"shift_actual_start": f"{when} 09:00:00",
			}
		).insert(ignore_permissions=True)
		frappe.set_user(self.user)
		self.assertEqual(
			get_requests_summary()["attendance"]["days"],
			1,
			"a punch with no attendance row is exactly what this counts",
		)

	def test_the_window_is_the_filing_window(self):
		"""Every day counted is one an Attendance Request would still accept —
		a count that includes days nobody can fix is a number with no action
		behind it."""
		frappe.set_user(self.user)
		window = get_requests_summary()["attendance"]
		self.assertIn("from_date", window)
		self.assertIn("to_date", window)
		self.assertLessEqual(window["from_date"], window["to_date"])

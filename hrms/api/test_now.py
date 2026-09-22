# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""The line at the top of Home.

It replaced "Last check-out was at 08:17 pm", which was true and made the
reader do the rest of the work. What is tested here is the two ways a status
line lies: saying a forgotten punch is a running session, and printing a
malformed time.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api.now import MAX_OPEN_SESSION_HOURS, _hhmm, get_now
from hrms.tests.test_utils import create_company


class TestTimeFormatting(FrappeTestCase):
	"""No site state: this is the formatter that put a trailing colon on the
	top line of Home."""

	def test_a_single_digit_hour_is_padded(self):
		"""A timedelta stringifies as "6:00:00", and slicing five characters
		off that gives "6:00:" — found on the bench against a real 22:00 to
		6:00 night shift."""
		self.assertEqual(_hhmm("6:00:00"), "06:00")
		self.assertEqual(_hhmm("22:00:00"), "22:00")
		self.assertEqual(_hhmm("0:30:00"), "00:30")

	def test_it_never_returns_a_trailing_colon(self):
		for value in ("6:00:00", "9:05:00", "23:59:00", "0:00:00"):
			self.assertFalse(_hhmm(value).endswith(":"), f"{value} formatted badly")
			self.assertEqual(len(_hhmm(value)), 5)

	def test_something_unparseable_comes_back_unchanged(self):
		"""Better a raw value on screen than an exception at the top of Home."""
		self.assertEqual(_hhmm("not a time"), "not a time")


class TestNowBar(FrappeTestCase):
	def setUp(self):
		self.company = create_company("_Test Now Bar").name
		self.user = "now_bar@example.com"
		self.employee = make_employee(self.user, company=self.company)
		frappe.db.delete("Employee Checkin", {"employee": self.employee})

	def tearDown(self):
		frappe.set_user("Administrator")

	def _punch(self, log_type, when):
		return frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": self.employee,
				"time": when,
				"log_type": log_type,
			}
		).insert(ignore_permissions=True)

	def _now(self):
		frappe.set_user(self.user)
		try:
			return get_now()
		finally:
			frappe.set_user("Administrator")

	def test_an_open_punch_is_a_running_session(self):
		self._punch("IN", add_to_date(now_datetime(), hours=-2))
		session = self._now()["session"]
		self.assertIsNotNone(session)
		self.assertGreater(session["hours"], 1.5)
		self.assertLess(session["hours"], 2.5)

	def test_a_closed_pair_is_not_a_session(self):
		"""Somebody who checked out is not working. A timer here would be the
		top of Home contradicting the button underneath it."""
		self._punch("IN", add_to_date(now_datetime(), hours=-9))
		self._punch("OUT", add_to_date(now_datetime(), hours=-1))
		self.assertIsNone(self._now()["session"])

	def test_a_forgotten_punch_is_not_a_session(self):
		"""The check-in button gives up on an open IN after 16 hours and offers
		IN again. A live timer beside it would be the screen contradicting
		itself, and the number would be nonsense besides."""
		self._punch("IN", add_to_date(now_datetime(), hours=-(MAX_OPEN_SESSION_HOURS + 2)))
		self.assertIsNone(self._now()["session"])

	def test_no_punches_at_all_is_not_an_error(self):
		"""A new employee's first morning. Every field answers; the session is
		simply absent."""
		payload = self._now()
		self.assertIsNone(payload["session"])
		self.assertIn("date", payload)
		self.assertIn("time", payload)

	def test_an_unresolvable_shift_does_not_take_the_line_down(self):
		"""The rest of the bar is still true. This is the first thing on the
		first screen — it may not 500."""
		payload = self._now()
		self.assertIn("shift", payload, "the key is always present")

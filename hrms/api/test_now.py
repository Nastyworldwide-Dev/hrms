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

from hrms.api.now import _hhmm, _state, get_now
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
		"""An IN past its session's end (06:00 the next morning, the rule the
		button and the punch share) is a forgotten punch, not a timer. A 16-hour
		cap here used to drop the timer while the person was still working
		(employee report, 25 Sep 2026); two days back is past any session."""
		self._punch("IN", add_to_date(now_datetime(), days=-2))
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


class TestStateWord(FrappeTestCase):
	"""Every employee is always in exactly one state.

	The bar shipped on 23 September with every part optional, so an employee
	with no shift assigned and no open punch got an empty line — and Home
	opened on the same "Last check-out was at 08:17 pm" it always had. A
	status line does not get to say nothing.
	"""

	def setUp(self):
		self.company = create_company("_Test Now State").name
		self.user = "now_state@example.com"
		self.employee = make_employee(self.user, company=self.company)
		frappe.db.delete("Employee Checkin", {"employee": self.employee})

	def tearDown(self):
		frappe.set_user("Administrator")

	def _now(self):
		frappe.set_user(self.user)
		try:
			return get_now()
		finally:
			frappe.set_user("Administrator")

	def test_there_is_always_a_state(self):
		"""The one assertion that would have caught the deploy. No punches, no
		shift — the emptiest an account can be — and the bar still has a word
		for it."""
		payload = self._now()
		self.assertIsNotNone(payload["state"])
		self.assertTrue(payload["state"]["label"], "a label a person can read")
		self.assertIn(payload["state"]["key"], ("working", "done", "before", "off"))

	def test_an_open_session_is_working(self):
		frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": self.employee,
				"time": add_to_date(now_datetime(), hours=-2),
				"log_type": "IN",
			}
		).insert(ignore_permissions=True)
		self.assertEqual(self._now()["state"]["key"], "working")

	def test_checked_out_today_is_done(self):
		for log_type, hours in (("IN", -8), ("OUT", -1)):
			frappe.get_doc(
				{
					"doctype": "Employee Checkin",
					"employee": self.employee,
					"time": add_to_date(now_datetime(), hours=hours),
					"log_type": log_type,
				}
			).insert(ignore_permissions=True)
		payload = self._now()
		self.assertEqual(payload["state"]["key"], "done")
		self.assertIsNotNone(payload["last_out"], "and it can say when")

	def test_nothing_at_all_is_off_rather_than_blank(self):
		"""A rest day is a fact. Saying it is better than an empty bar, which
		reads as a screen that failed to load."""
		self.assertEqual(self._now()["state"]["key"], "off")

	def test_the_last_out_is_not_read_while_a_session_runs(self):
		"""When somebody is checked IN, when they last left is not what the top
		of Home should be saying."""
		frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": self.employee,
				"time": add_to_date(now_datetime(), hours=-9),
				"log_type": "OUT",
			}
		).insert(ignore_permissions=True)
		frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": self.employee,
				"time": add_to_date(now_datetime(), hours=-2),
				"log_type": "IN",
			}
		).insert(ignore_permissions=True)
		payload = self._now()
		self.assertEqual(payload["state"]["key"], "working")
		self.assertIsNone(payload["last_out"])

	def test_the_state_is_pure_and_testable_on_its_own(self):
		"""The rule is a function of four inputs, so it can be exercised
		without a site — which is what makes every branch cheap to pin."""
		from frappe.utils import getdate

		now = now_datetime()
		today = str(getdate(now))
		self.assertEqual(_state({"since": "x"}, None, None, now)["key"], "working")
		self.assertEqual(_state(None, None, f"{today} 08:00:00", now)["key"], "done")
		self.assertEqual(_state(None, {"shift": "A"}, None, now)["key"], "before")
		self.assertEqual(_state(None, None, None, now)["key"], "off")
		# Yesterday's check-out is not today's "done" — that would tell
		# somebody their day was finished before it started.
		self.assertEqual(_state(None, None, "2000-01-01 08:00:00", now)["key"], "off")

# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""The month grid's flags.

The design rule this module exists to enforce: THE GRID CARRIES DOTS, THE DAY
SHEET CARRIES WORDS. A tile is about 44px — it holds a date and up to three
4px dots and nothing else — so what is tested here is the shape of the payload
as much as its contents.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api.calendar import FLAG_ORDER, MAX_DOTS, MAX_SPAN_DAYS, get_day, get_month_flags
from hrms.tests.test_utils import create_company


class TestMonthFlags(FrappeTestCase):
	def setUp(self):
		self.company = create_company("_Test Calendar").name
		self.user = "calendar_reader@example.com"
		self.employee = make_employee(self.user, company=self.company)
		self.start = add_days(nowdate(), -20)
		self.end = nowdate()

	def tearDown(self):
		frappe.set_user("Administrator")

	def _flags(self):
		frappe.set_user(self.user)
		try:
			return get_month_flags(self.start, self.end)
		finally:
			frappe.set_user("Administrator")

	def test_a_day_with_nothing_on_it_is_absent(self):
		"""Not present with an empty list. A month of empty arrays is a payload
		that says nothing in thirty lines, and the screen has to filter them
		out before it can count anything."""
		for day, flags in self._flags()["flags"].items():
			self.assertTrue(flags, f"{day} is listed with no flags")

	def test_no_tile_is_asked_to_draw_more_dots_than_it_can(self):
		"""Three is not a preference: it is what fits beside a two-digit date
		at 44px, and 44px is the tap-target floor the tile cannot go under.
		Capped in the PAYLOAD so the wire and the screen always agree."""
		for day, flags in self._flags()["flags"].items():
			self.assertLessEqual(len(flags), MAX_DOTS, f"{day} has {len(flags)} dots")

	def test_the_dot_order_is_fixed(self):
		"""A person learns the position rather than re-reading the legend: the
		first dot is always "you were off", never sometimes something else."""
		order = {name: index for index, name in enumerate(FLAG_ORDER)}
		for day, flags in self._flags()["flags"].items():
			positions = [order[flag] for flag in flags]
			self.assertEqual(positions, sorted(positions), f"{day} is out of order")

	def test_the_legend_is_the_order(self):
		"""One list, so the legend cannot describe a different sequence from
		the one the tiles draw."""
		self.assertEqual(self._flags()["legend"], list(FLAG_ORDER))

	def test_a_worked_day_with_no_attendance_needs_you(self):
		"""The most expensive kind of missing day: it is invisible until
		payroll, and by then the window to fix it has usually closed."""
		day = add_days(nowdate(), -3)
		frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": self.employee,
				"time": f"{day} 09:00:00",
				"log_type": "IN",
				"shift_actual_start": f"{day} 09:00:00",
			}
		).insert(ignore_permissions=True)
		self.assertIn("needs_you", self._flags()["flags"].get(str(day), []))

	def test_a_day_nobody_worked_does_not_need_you(self):
		"""It is a day off. A dot there is a prompt with no action behind it,
		on a tile that will carry it forever."""
		flags = self._flags()["flags"]
		day = str(add_days(nowdate(), -19))
		self.assertNotIn("needs_you", flags.get(day, []))

	def test_a_leave_application_still_waiting_is_not_a_day_off(self):
		"""Marking a pending request as leave on the grid is how somebody books
		a flight against leave that is later rejected."""
		leave_type = frappe.db.get_value("Leave Type", {}, "name")
		day = add_days(nowdate(), -5)
		frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": self.employee,
				"leave_type": leave_type,
				"from_date": day,
				"to_date": day,
				"status": "Open",
				"company": self.company,
			}
		).insert(ignore_permissions=True)
		self.assertNotIn("leave", self._flags()["flags"].get(str(day), []))

	def test_a_month_is_the_most_anybody_may_ask_for(self):
		"""A caller asking for two years is a bug or a scrape, and either way
		it is a table scan per employee."""
		frappe.set_user(self.user)
		self.assertRaises(
			frappe.ValidationError,
			get_month_flags,
			add_days(nowdate(), -(MAX_SPAN_DAYS + 5)),
			nowdate(),
		)

	def test_a_backwards_window_is_refused(self):
		frappe.set_user(self.user)
		self.assertRaises(frappe.ValidationError, get_month_flags, nowdate(), add_days(nowdate(), -5))

	def test_the_event_dot_uses_the_announcement_fence(self):
		"""An Event dot on a day whose announcement the reader may not see
		would tell them something is happening and refuse to say what."""
		import inspect

		from hrms.api import calendar

		source = inspect.getsource(calendar._event_days)
		self.assertIn("from hrms.api.announcements import _reader, _visible_rows", source)


class TestDaySheet(FrappeTestCase):
	"""One day, and only the sections the caller is entitled to.

	The rule (revamp P5/KR2): PERSONA IS THE SERVER'S ANSWER. The PWA renders
	whatever arrives and holds no role logic, so there is nothing on that side
	to get wrong and nothing to keep in step with this.
	"""

	def setUp(self):
		self.company = create_company("_Test Day Sheet").name
		self.boss_user = "day_sheet_boss@example.com"
		self.staff_user = "day_sheet_staff@example.com"
		self.bystander_user = "day_sheet_other@example.com"
		self.boss = make_employee(self.boss_user, company=self.company)
		self.staff = make_employee(self.staff_user, company=self.company)
		self.bystander = make_employee(self.bystander_user, company=self.company)
		frappe.db.set_value("Employee", self.staff, "reports_to", self.boss)
		self.day = add_days(nowdate(), -4)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _as(self, user):
		frappe.set_user(user)
		try:
			return get_day(str(self.day))
		finally:
			frappe.set_user("Administrator")

	def test_an_employee_gets_their_own_day_and_nothing_else(self):
		sections = self._as(self.staff_user)
		self.assertEqual(sorted(sections), ["me"])

	def test_an_approver_additionally_gets_their_line(self):
		sections = self._as(self.boss_user)
		self.assertIn("team_off", sections)
		self.assertIn("coverage", sections)
		self.assertEqual(sections["coverage"]["headcount"], 1)

	def test_a_bystander_gets_no_team_section_at_all(self):
		"""Absent, not empty. An empty list would tell somebody they have a
		team and it is all present, which is a different false statement."""
		sections = self._as(self.bystander_user)
		self.assertNotIn("team_off", sections)
		self.assertNotIn("coverage", sections)

	def test_a_manager_never_sees_why_somebody_is_off(self):
		"""Owner's ruling, 22 Sep 2026: type yes, reason never. A leave reason
		is between the employee, their approver and HR."""
		leave_type = frappe.db.get_value("Leave Type", {}, "name")
		application = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": self.staff,
				"leave_type": leave_type,
				"from_date": self.day,
				"to_date": self.day,
				"status": "Approved",
				"description": "a private medical matter",
				"company": self.company,
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value("Leave Application", application.name, "docstatus", 1)

		for row in self._as(self.boss_user)["team_off"]:
			self.assertNotIn("description", row)
			self.assertNotIn("reason", row)
			self.assertIn("leave_type", row, "the TYPE is allowed")

	def test_the_reporting_line_is_derived_from_identity(self):
		"""Never from anything the caller sends — there is no employee or team
		argument, so there is no shape in which somebody asks for another
		manager's day."""
		import inspect

		from hrms.api import calendar

		self.assertEqual(list(inspect.signature(calendar.get_day).parameters), ["date"])
		source = inspect.getsource(calendar.get_day)
		# Direct reports since owner ruling 1 (23 Sep 2026).
		self.assertIn("get_direct_report_employees(frappe.session.user)", source)

	def test_a_skipped_punch_is_shown_rather_than_hidden(self):
		""" "My tap is missing" and "my tap was set aside" are different
		problems with different answers, and hiding the second makes it look
		like the first."""
		frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": self.staff,
				"time": f"{self.day} 09:00:00",
				"log_type": "IN",
				"skip_auto_attendance": 1,
			}
		).insert(ignore_permissions=True)
		punches = self._as(self.staff_user)["me"]["punches"]
		self.assertEqual(len(punches), 1)
		self.assertTrue(punches[0]["skipped"], "a set-aside tap says so")

	def test_a_day_must_be_named(self):
		frappe.set_user(self.staff_user)
		for value in (None, "", "   ", {"date": "x"}):
			with self.assertRaises((frappe.PermissionError, frappe.ValidationError, TypeError)):
				get_day(value)

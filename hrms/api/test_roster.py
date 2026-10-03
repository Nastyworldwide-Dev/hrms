# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Fence guard for the roster write path (hrms.api.roster._ensure_can_roster).

The invariant, in a multi-company hub that serves everyone (not just HR): a
Shift Supervisor may roster their OWN direct reports and no one else, HR may
roster within their company fence, and a plain employee may roster nobody.
Unwired or loosened, one branch leader could touch another team's — or another
company's — roster. These tests fail the build if that boundary slips.

    bench --site <site> run-tests --app hrms --module hrms.api.test_roster
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms.api.roster import ROSTER_SUPERVISOR_ROLE, _ensure_can_roster
from hrms.patches.v16_0.add_shift_supervisor_role import execute as ensure_role

COMPANY = "_Test Company"


def _make_user(email: str, roles: list[str]) -> str:
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		)
		user.flags.ignore_permissions = True
		user.insert()
	else:
		user = frappe.get_doc("User", email)
	for role in roles:
		if role not in {r.role for r in user.roles}:
			user.append("roles", {"role": role})
	user.flags.ignore_permissions = True
	user.save()
	return email


def _make_employee(email: str, roles: list[str], reports_to: str | None = None) -> str:
	user = _make_user(email, ["Employee", *roles])
	existing = frappe.db.get_value("Employee", {"user_id": user})
	if existing:
		frappe.db.set_value("Employee", existing, "reports_to", reports_to)
		return existing
	emp = frappe.get_doc(
		{
			"doctype": "Employee",
			"first_name": email.split("@")[0],
			"company": COMPANY,
			"user_id": user,
			"date_of_joining": "2020-01-01",
			"date_of_birth": "1990-01-01",
			"gender": "Other",
			"status": "Active",
			"reports_to": reports_to,
		}
	)
	emp.flags.ignore_permissions = True
	emp.insert()
	return emp.name


class TestRosterFence(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_role()  # the Shift Supervisor role must exist to be assigned
		cls.supervisor = _make_employee("roster.sv@bench.test", [ROSTER_SUPERVISOR_ROLE])
		cls.report = _make_employee("roster.report@bench.test", [], reports_to=cls.supervisor)
		cls.stranger = _make_employee("roster.stranger@bench.test", [])  # not their report
		cls.hr = _make_employee("roster.hr@bench.test", ["HR User"])
		cls.plain = _make_employee("roster.plain@bench.test", [])

	def tearDown(self):
		frappe.set_user("Administrator")

	def _as(self, employee):
		frappe.set_user(frappe.db.get_value("Employee", employee, "user_id"))

	def test_supervisor_can_roster_own_report(self):
		self._as(self.supervisor)
		_ensure_can_roster(self.report)  # must not throw

	def test_supervisor_cannot_roster_a_non_report(self):
		self._as(self.supervisor)
		with self.assertRaises(frappe.PermissionError):
			_ensure_can_roster(self.stranger)

	def test_supervisor_can_roster_themselves(self):
		# Owner, 30 Sep 2026: a Shift Supervisor assigns their own shifts too
		# (hrms.hr.utils.rostered_employees).
		self._as(self.supervisor)
		_ensure_can_roster(self.supervisor)  # must not throw

	def test_plain_employee_can_roster_nobody(self):
		self._as(self.plain)
		with self.assertRaises(frappe.PermissionError):
			_ensure_can_roster(self.report)
		with self.assertRaises(frappe.PermissionError):
			_ensure_can_roster(self.plain)

	def test_hr_can_roster_within_company(self):
		self._as(self.hr)
		_ensure_can_roster(self.report)  # must not throw
		_ensure_can_roster(self.stranger)

	def test_unknown_employee_is_rejected(self):
		self._as(self.hr)
		with self.assertRaises(frappe.DoesNotExistError):
			_ensure_can_roster("EMP-does-not-exist-xyz")

	def test_supervisor_role_without_reporting_line_is_not_enough(self):
		# holding the role but the target is someone else's report -> denied.
		# The role is capability; the reports_to link is authority.
		self._as(self.supervisor)
		with self.assertRaises(frappe.PermissionError):
			_ensure_can_roster(self.stranger)


def _shift_type(name: str, start: str, end: str) -> str:
	if not frappe.db.exists("Shift Type", name):
		frappe.get_doc(
			{"doctype": "Shift Type", "__newname": name, "start_time": start, "end_time": end}
		).insert()
	return name


class TestSupervisorEditsRoster(FrappeTestCase):
	"""Owner, 2 Oct 2026: a Shift Supervisor changes and removes their own
	team's shifts from Nadi, with no lock — except a day already worked
	(punches or attendance), which stays for HR (ruling a)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_role()
		cls.supervisor = _make_employee("roster.sv@bench.test", [ROSTER_SUPERVISOR_ROLE])
		cls.report = _make_employee("roster.report@bench.test", [], reports_to=cls.supervisor)
		cls.stranger = _make_employee("roster.stranger@bench.test", [])
		cls.day_shift = _shift_type("_Roster Day", "08:00:00", "12:00:00")
		cls.late_shift = _shift_type("_Roster Late", "14:00:00", "18:00:00")

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.delete("Shift Assignment", {"employee": ("in", [self.report, self.stranger])})
		frappe.db.delete("Employee Checkin", {"employee": ("in", [self.report, self.stranger])})

	def tearDown(self):
		frappe.set_user("Administrator")

	def _week(self, employee):
		doc = frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"shift_type": self.day_shift,
				"company": COMPANY,
				"employee": employee,
				"start_date": "2031-03-03",
				"end_date": "2031-03-09",
			}
		)
		doc.submit()
		return doc.name

	def _as_supervisor(self):
		frappe.set_user(frappe.db.get_value("Employee", self.supervisor, "user_id"))

	def _days(self, employee):
		rows = frappe.get_all(
			"Shift Assignment",
			filters={"employee": employee, "docstatus": 1},
			fields=["shift_type", "start_date", "end_date"],
			order_by="start_date",
		)
		return [(r.shift_type, str(r.start_date), str(r.end_date)) for r in rows]

	def test_supervisor_removes_a_middle_day(self):
		from hrms.api.roster import remove_shift_day

		name = self._week(self.report)
		self._as_supervisor()
		remove_shift_day(name, "2031-03-05")
		frappe.set_user("Administrator")
		self.assertEqual(
			self._days(self.report),
			[(self.day_shift, "2031-03-03", "2031-03-04"), (self.day_shift, "2031-03-06", "2031-03-09")],
		)

	def test_supervisor_removes_the_first_day(self):
		# The first day is a cancel + delete, which the role alone may not do.
		from hrms.api.roster import remove_shift_day

		name = self._week(self.report)
		self._as_supervisor()
		remove_shift_day(name, "2031-03-03")
		frappe.set_user("Administrator")
		self.assertEqual(self._days(self.report), [(self.day_shift, "2031-03-04", "2031-03-09")])

	def test_supervisor_changes_one_day_to_another_shift(self):
		from hrms.api.roster import change_shift_day

		name = self._week(self.report)
		self._as_supervisor()
		change_shift_day(name, "2031-03-05", self.late_shift)
		frappe.set_user("Administrator")
		self.assertEqual(
			self._days(self.report),
			[
				(self.day_shift, "2031-03-03", "2031-03-04"),
				(self.late_shift, "2031-03-05", "2031-03-05"),
				(self.day_shift, "2031-03-06", "2031-03-09"),
			],
		)

	def test_worked_day_is_refused(self):
		from hrms.api.roster import remove_shift_day

		name = self._week(self.report)
		frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": self.report,
				"time": "2031-03-05 08:02:00",
				"log_type": "IN",
			}
		).insert(ignore_permissions=True)
		self._as_supervisor()
		with self.assertRaisesRegex(frappe.ValidationError, "Ask HR"):
			remove_shift_day(name, "2031-03-05")

	def test_supervisor_cannot_remove_another_teams_shift(self):
		from hrms.api.roster import remove_shift_day

		name = self._week(self.stranger)
		self._as_supervisor()
		with self.assertRaises(frappe.PermissionError):
			remove_shift_day(name, "2031-03-05")

	def test_hr_user_changes_a_day_from_the_desk_roster(self):
		# HR, 2 Oct 2026 ("asal aku takleh update?"): the Desk Roster now sends a
		# shift-type change here. HR User holds no cancel/delete on Shift
		# Assignment, so a first-day change must still go through for them.
		from hrms.api.roster import change_shift_day

		hr = _make_employee("roster.hr@bench.test", ["HR User"])
		name = self._week(self.stranger)
		frappe.set_user(frappe.db.get_value("Employee", hr, "user_id"))
		change_shift_day(name, "2031-03-03", self.late_shift)
		frappe.set_user("Administrator")
		self.assertEqual(
			self._days(self.stranger),
			[(self.late_shift, "2031-03-03", "2031-03-03"), (self.day_shift, "2031-03-04", "2031-03-09")],
		)

	def test_hr_is_not_told_to_ask_hr(self):
		from hrms.api.roster import remove_shift_day

		hr = _make_employee("roster.hr@bench.test", ["HR User"])
		name = self._week(self.stranger)
		frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": self.stranger,
				"time": "2031-03-05 08:02:00",
				"log_type": "IN",
			}
		).insert(ignore_permissions=True)
		frappe.set_user(frappe.db.get_value("Employee", hr, "user_id"))
		with self.assertRaises(frappe.ValidationError) as caught:
			remove_shift_day(name, "2031-03-05")
		self.assertNotIn("Ask HR", str(caught.exception))

	def test_one_day_becomes_a_public_holiday(self):
		# HR, 2 Oct 2026: the roster's Day Type sets the day's rate. One day in a
		# week-long shift is marked Public Holiday; the rest keep their type.
		from hrms.api.roster import change_shift_day

		name = self._week(self.report)
		self._as_supervisor()
		change_shift_day(name, "2031-03-05", self.day_shift, day_type="Public Holiday")
		frappe.set_user("Administrator")
		rows = frappe.get_all(
			"Shift Assignment",
			filters={"employee": self.report, "docstatus": 1},
			fields=["start_date", "end_date", "day_type"],
			order_by="start_date",
		)
		self.assertEqual(
			[(str(r.start_date), str(r.end_date), r.day_type) for r in rows],
			[
				("2031-03-03", "2031-03-04", "None"),
				("2031-03-05", "2031-03-05", "Public Holiday"),
				("2031-03-06", "2031-03-09", "None"),
			],
		)

	def test_an_unknown_day_type_is_refused(self):
		from hrms.api.roster import insert_shift

		self._as_supervisor()
		with self.assertRaises(frappe.ValidationError):
			insert_shift(
				self.report, COMPANY, self.day_shift, "2031-04-01", "2031-04-01", "Active", day_type="Holiday"
			)

	def test_a_repeating_schedule_carries_its_day_type(self):
		# A long shift with repeat days is saved through the schedule endpoint;
		# its Day Type must reach every shift it creates.
		from hrms.api.roster import create_shift_schedule_assignment

		frappe.db.delete("Shift Schedule Assignment", {"employee": self.report})
		create_shift_schedule_assignment(
			employee=self.report,
			company=COMPANY,
			shift_type=self.day_shift,
			status="Active",
			start_date="2031-05-05",
			end_date="2031-05-18",
			repeat_on_days=["Monday", "Wednesday"],
			frequency="Every Week",
			day_type="Off Day",
		)
		types = set(
			frappe.get_all(
				"Shift Assignment",
				filters={"employee": self.report, "start_date": (">=", "2031-05-05")},
				pluck="day_type",
			)
		)
		self.assertEqual(types, {"Off Day"})

	def test_supervisor_deletes_a_whole_assignment(self):
		# Fahmie, 3 Oct 2026: "Delete -> All Consecutive Shifts" refused a Shift
		# Supervisor (Frappe cancel/delete check). The roster fence decides now.
		from hrms.api.roster import delete_shift_assignment

		name = self._week(self.report)
		self._as_supervisor()
		delete_shift_assignment(name)
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("Shift Assignment", name))

	def test_supervisor_updates_status_and_end_date(self):
		from hrms.api.roster import update_shift_assignment

		name = self._week(self.report)
		self._as_supervisor()
		update_shift_assignment(name, "Active", "2031-03-06")
		frappe.set_user("Administrator")
		self.assertEqual(str(frappe.db.get_value("Shift Assignment", name, "end_date")), "2031-03-06")

	def test_supervisor_deletes_a_repeating_schedule(self):
		from hrms.api.roster import create_shift_schedule_assignment, delete_shift_schedule_assignment

		frappe.db.delete("Shift Schedule Assignment", {"employee": self.report})
		frappe.set_user("Administrator")
		create_shift_schedule_assignment(
			employee=self.report,
			company=COMPANY,
			shift_type=self.day_shift,
			status="Active",
			start_date="2031-07-07",
			end_date="2031-07-20",
			repeat_on_days=["Monday"],
			frequency="Every Week",
		)
		schedule = frappe.db.get_value("Shift Schedule Assignment", {"employee": self.report})
		self._as_supervisor()
		delete_shift_schedule_assignment(schedule)
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.exists("Shift Schedule Assignment", schedule))
		self.assertFalse(frappe.db.exists("Shift Assignment", {"shift_schedule_assignment": schedule}))

	def test_a_stranger_cannot_be_deleted_or_updated(self):
		from hrms.api.roster import delete_shift_assignment, update_shift_assignment

		name = self._week(self.stranger)
		self._as_supervisor()
		with self.assertRaises(frappe.PermissionError):
			delete_shift_assignment(name)
		with self.assertRaises(frappe.PermissionError):
			update_shift_assignment(name, "Inactive", None)

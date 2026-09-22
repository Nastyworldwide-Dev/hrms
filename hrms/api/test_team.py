# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Fence guard for the Nadi Team Roster read (hrms.api.team.get_team_roster).

The invariant: a leader sees ONLY their own direct reports' roster; a non-HR
caller cannot browse another manager's team; a plain employee sees nothing.
Same boundary as the team status view — pinned so the roster read can't drift
into leaking another team's or another company's shifts.

    bench --site <site> run-tests --app hrms --module hrms.api.test_team
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from hrms.api.team import get_team_roster, get_team_status

COMPANY = "_Test Company"


def _make_user(email, roles):
	if not frappe.db.exists("User", email):
		u = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		)
		u.flags.ignore_permissions = True
		u.insert()
	else:
		u = frappe.get_doc("User", email)
	for r in roles:
		if r not in {x.role for x in u.roles}:
			u.append("roles", {"role": r})
	u.flags.ignore_permissions = True
	u.save()
	return email


def _make_employee(email, roles, reports_to=None):
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


class TestTeamRosterFence(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if not frappe.db.exists("Shift Type", "_Team Roster Shift"):
			frappe.get_doc(
				{
					"doctype": "Shift Type",
					"name": "_Team Roster Shift",
					"start_time": "09:00:00",
					"end_time": "18:00:00",
				}
			).insert(ignore_permissions=True)
		cls.leader = _make_employee("tr.leader@bench.test", [])
		cls.report = _make_employee("tr.report@bench.test", [], reports_to=cls.leader)
		cls.other_leader = _make_employee("tr.other@bench.test", [])
		cls.plain = _make_employee("tr.plain@bench.test", [])
		cls.hr = _make_employee("tr.hr@bench.test", ["HR User"])
		sa = frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"employee": cls.report,
				"company": COMPANY,
				"shift_type": "_Team Roster Shift",
				"start_date": nowdate(),
				"status": "Active",
			}
		)
		sa.flags.ignore_permissions = True
		sa.insert()
		sa.submit()

	def tearDown(self):
		frappe.set_user("Administrator")

	def _as(self, employee):
		frappe.set_user(frappe.db.get_value("Employee", employee, "user_id"))

	def _week(self):
		return {"start_date": nowdate(), "end_date": add_days(nowdate(), 6)}

	def test_leader_sees_own_report_and_their_shift(self):
		self._as(self.leader)
		out = get_team_roster(**self._week())
		names = [m["name"] for m in out["members"]]
		self.assertIn(self.report, names)
		member = next(m for m in out["members"] if m["name"] == self.report)
		self.assertTrue(any(s["shift_type"] == "_Team Roster Shift" for s in member["shifts"]))

	def test_plain_employee_sees_empty_roster(self):
		self._as(self.plain)
		out = get_team_roster(**self._week())
		self.assertEqual(out["members"], [])

	def test_non_hr_cannot_browse_another_managers_team(self):
		self._as(self.other_leader)
		with self.assertRaises(frappe.PermissionError):
			get_team_roster(manager=self.leader, **self._week())

	def test_hr_may_browse_a_named_managers_team(self):
		self._as(self.hr)
		out = get_team_roster(manager=self.leader, **self._week())
		self.assertIn(self.report, [m["name"] for m in out["members"]])


class TestTeamEntitlement(FrappeTestCase):
	"""Two different empties, and saying the wrong one is a false statement
	about somebody's job.

	Until 22 Sep 2026 "you have no team" and "your team has nobody today"
	returned the same payload, so an employee who is nobody's manager was told
	"approvals will appear here when your team submits" — about a team they do
	not have. The screen could not tell them apart because the server did not.
	"""

	def setUp(self):
		# This module's own helpers, not erpnext's: they create the User as
		# well as the Employee and wire reports_to in one call, which is what
		# every other class here uses.
		self.boss_user = "team_ent_boss@bench.test"
		self.staff_user = "team_ent_staff@bench.test"
		self.boss = _make_employee(self.boss_user, [])
		self.staff = _make_employee(self.staff_user, [], reports_to=self.boss)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _status(self, user):
		frappe.set_user(user)
		try:
			return get_team_status(nowdate())
		finally:
			frappe.set_user("Administrator")

	def test_a_manager_is_entitled(self):
		status = self._status(self.boss_user)
		self.assertTrue(status["entitled"])
		self.assertEqual(len(status["members"]), 1)

	def test_somebody_who_manages_nobody_is_not(self):
		"""The defect this fixes. `team_of` falls back to the caller's own
		employee id, so an early "no team_of" check only ever caught somebody
		with no Employee record at all — every ordinary employee came back
		entitled and was told their team was quiet today."""
		status = self._status(self.staff_user)
		self.assertFalse(status["entitled"])
		self.assertEqual(status["members"], [])

	def test_a_manager_whose_reports_left_is_still_entitled(self):
		"""A different position from somebody who was never a manager, and the
		screen says two different things about it."""
		frappe.db.set_value("Employee", self.staff, "status", "Left")
		try:
			status = self._status(self.boss_user)
			self.assertTrue(
				status["entitled"], "an approver with nobody active still has the screen"
			)
			self.assertEqual(status["members"], [])
		finally:
			frappe.db.set_value("Employee", self.staff, "status", "Active")

	def test_entitlement_uses_the_app_s_one_definition(self):
		"""`is_approver` already answers "does anything route to this person"
		for the RequestPanel's team tabs. Two definitions of that would drift,
		and the drift would be somebody told they have no team while their
		approvals pile up."""
		import inspect

		from hrms.api import team

		self.assertIn("entitled = is_approver()", inspect.getsource(team.get_team_status))

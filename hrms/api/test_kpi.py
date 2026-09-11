# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import inspect

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.designation.test_designation import create_designation
from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api.kpi import CEO_DESIGNATION, can_view_team_kpi, get_my_kpi_dashboard, get_team_kpi
from hrms.hr.doctype.appraisal_cycle.test_appraisal_cycle import create_appraisal_cycle
from hrms.hr.doctype.appraisal_template.test_appraisal_template import create_appraisal_template
from hrms.tests.test_utils import create_company


class TestMyKPIDashboard(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Goal")
		frappe.db.delete("Appraisal")
		frappe.db.delete("Employee Performance Feedback")

		self.company = create_company("_Test Appraisal").name
		self.template = create_appraisal_template()

		engineer = create_designation(designation_name="Engineer")
		engineer.appraisal_template = self.template.name
		engineer.save()

		self.user_a = "kpi_dash_a@example.com"
		self.user_b = "kpi_dash_b@example.com"
		self.emp_a = make_employee(self.user_a, company=self.company, designation="Engineer")
		self.emp_b = make_employee(self.user_b, company=self.company, designation="Engineer")

		self.cycle = create_appraisal_cycle(designation="Engineer")
		self.cycle.create_appraisals()

		self.appraisal_a = frappe.db.get_value(
			"Appraisal", {"appraisal_cycle": self.cycle.name, "employee": self.emp_a}
		)
		self.appraisal_b = frappe.db.get_value(
			"Appraisal", {"appraisal_cycle": self.cycle.name, "employee": self.emp_b}
		)
		frappe.db.set_value("Appraisal", self.appraisal_a, "pms_total_score", 81.5)
		frappe.db.set_value("Appraisal", self.appraisal_b, "pms_total_score", 55.0)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_returns_only_own_appraisal_data(self):
		frappe.set_user(self.user_a)
		data = get_my_kpi_dashboard()

		self.assertEqual(data["employee"]["name"], self.emp_a)
		self.assertEqual(data["current"]["appraisal"], self.appraisal_a)
		self.assertEqual(data["current"]["total_score"], 81.5)
		self.assertIsInstance(data["current"]["kras"], list)
		self.assertIsInstance(data["feedback"]["count"], int)

		returned = {h["appraisal"] for h in data["history"]}
		self.assertIn(self.appraisal_a, returned)
		self.assertNotIn(self.appraisal_b, returned)

	def test_other_employees_scores_are_not_leaked(self):
		frappe.set_user(self.user_b)
		data = get_my_kpi_dashboard()

		self.assertEqual(data["employee"]["name"], self.emp_b)
		self.assertEqual(data["current"]["appraisal"], self.appraisal_b)
		self.assertEqual(data["current"]["total_score"], 55.0)
		self.assertNotIn(self.appraisal_a, {h["appraisal"] for h in data["history"]})

	def test_takes_no_employee_argument(self):
		# The endpoint must never accept a target employee: the appraisal
		# visibility hooks do not protect whitelisted endpoints, so scope
		# is enforced by deriving the employee from the session user only.
		# Only presentation filters (year / cycle) are permitted.
		self.assertEqual(list(inspect.signature(get_my_kpi_dashboard).parameters), ["year", "cycle"])

	def _create_second_cycle(self, score: float):
		cycle = create_appraisal_cycle(
			designation="Engineer", name="Q2", start_date="2022-04-01", end_date="2022-06-30"
		)
		cycle.create_appraisals()
		appraisal = frappe.db.get_value("Appraisal", {"appraisal_cycle": cycle.name, "employee": self.emp_a})
		frappe.db.set_value("Appraisal", appraisal, "pms_total_score", score)
		return appraisal

	def test_cycle_filter_selects_specific_appraisal(self):
		self._create_second_cycle(60.5)

		frappe.set_user(self.user_a)
		data = get_my_kpi_dashboard(year=2022, cycle="Q1")

		self.assertEqual(data["current"]["appraisal"], self.appraisal_a)
		self.assertEqual(data["current"]["total_score"], 81.5)
		self.assertEqual(data["selected_year"], 2022)
		self.assertEqual(data["selected_cycle"], "Q1")
		self.assertEqual(set(data["cycles"]), {"Q1", "Q2"})

	def test_all_cycles_averages_across_the_year(self):
		self._create_second_cycle(60.5)

		frappe.set_user(self.user_a)
		data = get_my_kpi_dashboard(year=2022, cycle="_all")

		self.assertTrue(data["current"]["is_average"])
		self.assertEqual(data["current"]["cycles_count"], 2)
		self.assertAlmostEqual(data["current"]["total_score"], (81.5 + 60.5) / 2)
		self.assertIsNone(data["current"]["grade"])
		self.assertIsNone(data["previous_score"])
		self.assertEqual(data["selected_cycle"], "_all")
		self.assertEqual(len(data["history"]), 2)
		self.assertIn(2022, data["years"])

	def test_all_cycles_preserves_distinct_kpis(self):
		# Regression: _year_average grouped by KRA name alone, collapsing sibling
		# KPIs that share a KRA (e.g. three "Product Presence" KPIs) into one row,
		# so the "All Appraisal Cycles" view no longer matched the single cycle.
		# With one cycle in the year, ALL_CYCLES must present the same (KRA, KPI)
		# rows and same total as selecting that cycle.
		frappe.set_user(self.user_a)
		single = get_my_kpi_dashboard(year=2022, cycle=self.cycle.name)
		allc = get_my_kpi_dashboard(year=2022, cycle="_all")

		single_pairs = sorted((k["kra"], k["kpi"]) for k in single["current"]["kras"])
		all_pairs = sorted((k["kra"], k["kpi"]) for k in allc["current"]["kras"])
		self.assertEqual(all_pairs, single_pairs)
		self.assertEqual(allc["current"]["total_score"], single["current"]["total_score"])

	def test_year_without_appraisals_returns_empty_current(self):
		frappe.set_user(self.user_a)
		data = get_my_kpi_dashboard(year=1999)

		self.assertIsNone(data["current"])
		self.assertEqual(data["cycles"], [])
		self.assertEqual(data["selected_year"], 1999)
		self.assertIn(2022, data["years"])

	def test_appraisal_without_own_dates_resolves_via_cycle(self):
		# Regression (v15.94.0): the year filter grouped appraisals by
		# getdate(end_date).year and dropped any appraisal whose own end_date was
		# empty. NHSB-style appraisals leave start_date/end_date blank and carry
		# the period only on their Appraisal Cycle, so My KPI blanked out. The
		# effective date must fall back to the cycle's dates.
		frappe.db.set_value("Appraisal", self.appraisal_a, {"start_date": None, "end_date": None})

		frappe.set_user(self.user_a)
		data = get_my_kpi_dashboard()

		self.assertIsNotNone(data["current"], "appraisal with no own dates must still appear")
		self.assertEqual(data["current"]["appraisal"], self.appraisal_a)
		# cycle end_date is 2022-03-31 -> year 2022
		self.assertIn(2022, data["years"])
		self.assertEqual(data["selected_year"], 2022)

	def test_appraisal_without_any_dates_falls_back_to_creation(self):
		# Even with no dates anywhere (appraisal and cycle both blank), the
		# appraisal must still surface, bucketed by its creation year.
		frappe.db.set_value("Appraisal", self.appraisal_a, {"start_date": None, "end_date": None})
		frappe.db.set_value("Appraisal Cycle", self.cycle.name, {"start_date": None, "end_date": None})

		frappe.set_user(self.user_a)
		data = get_my_kpi_dashboard()

		self.assertIsNotNone(data["current"])
		self.assertEqual(data["current"]["appraisal"], self.appraisal_a)

	def test_user_without_employee_is_rejected(self):
		# "test@example.com" is an erpnext fixture user and DOES carry an active
		# Employee (_T-Employee-00001), so it never exercised this path. Use a
		# user with no Employee at all — the case _get_session_employee guards.
		email = "kpi_no_employee@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "No Employee", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
		self.assertFalse(frappe.db.exists("Employee", {"user_id": email, "status": "Active"}))

		frappe.set_user(email)
		self.assertRaises(frappe.PermissionError, get_my_kpi_dashboard)

	def test_employee_without_appraisals_gets_empty_state(self):
		frappe.db.delete("Appraisal", {"employee": self.emp_a})
		frappe.set_user(self.user_a)
		data = get_my_kpi_dashboard()

		self.assertIsNone(data["current"])
		self.assertEqual(data["history"], [])
		self.assertEqual(data["feedback"]["count"], 0)


class TestTeamKPI(FrappeTestCase):
	"""Team KPI has TWO allowlists, and they are different in kind.

	  CEO  — by DESIGNATION on the Employee record. The office, not a role.
	  HR   — by ROLE (HR User / HR Manager), the same predicate that already
	         governs every other HR-only surface in this app.

	A designation gate was chosen for the CEO precisely because roles on this
	hub are bundled into role profiles, so "the CEO" is not expressible as a
	role. HR is the opposite case: it IS a role, and reusing is_hr_operator
	means Team KPI can never drift from the rest of the HR surfaces.

	Both see every company they are permitted, which for an unfenced user is
	all of them; a Company User Permission narrows either of them identically.
	Everyone else — System Manager included — is refused.
	"""

	def setUp(self):
		frappe.db.delete("Goal")
		frappe.db.delete("Appraisal")
		frappe.db.delete("User Permission", {"allow": "Company"})

		self.company = create_company("_Test Team KPI").name
		self.other_company = create_company("_Test Team KPI Two").name
		self.template = create_appraisal_template()

		engineer = create_designation(designation_name="Engineer")
		engineer.appraisal_template = self.template.name
		engineer.save()
		create_designation(designation_name=CEO_DESIGNATION)

		self.sales = self._department("Sales TK", self.company)
		self.ops = self._department("Ops TK", self.company)
		self.far = self._department("Far TK", self.other_company)

		self.ceo_user = "team_kpi_ceo@example.com"
		self.staff_user = "team_kpi_staff@example.com"
		self.ops_user = "team_kpi_ops@example.com"
		self.hr_user = "team_kpi_hr@example.com"
		self.far_user = "team_kpi_far@example.com"

		self.ceo = self._employee(self.ceo_user, CEO_DESIGNATION, self.sales, self.company)
		self.staff = self._employee(self.staff_user, "Engineer", self.sales, self.company)
		self.ops_emp = self._employee(self.ops_user, "Engineer", self.ops, self.company)
		self.far_emp = self._employee(self.far_user, "Engineer", self.far, self.other_company)
		self.hr = self._employee(self.hr_user, "Engineer", self.ops, self.company)
		frappe.get_doc("User", self.hr_user).add_roles("HR Manager")

		self.scores = {self.staff: 90.0, self.ops_emp: 40.0, self.far_emp: 70.0}
		self.appraisals = {
			employee: self._appraisal(employee, score) for employee, score in self.scores.items()
		}

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.delete("User Permission", {"allow": "Company"})

	def _department(self, name: str, company: str) -> str:
		return (
			frappe.get_doc({"doctype": "Department", "department_name": name, "company": company})
			.insert(ignore_permissions=True, ignore_if_duplicate=True)
			.name
		)

	def _employee(self, user: str, designation: str, department: str, company: str) -> str:
		employee = make_employee(user, company=company, designation=designation)
		frappe.db.set_value("Employee", employee, "department", department)
		return employee

	def _appraisal(
		self,
		employee: str,
		score: float,
		start_date: str = "2026-01-01",
		end_date: str = "2026-03-31",
	) -> str:
		# Appraisal.validate_duplicate refuses a second appraisal for the same
		# employee over an OVERLAPPING period, so a second cycle needs its own
		# dates rather than just its own name.
		company = frappe.db.get_value("Employee", employee, "company")
		doc = frappe.get_doc(
			{
				"doctype": "Appraisal",
				"employee": employee,
				"company": company,
				"start_date": start_date,
				"end_date": end_date,
				"overall_grade": "A",
			}
		).insert(ignore_permissions=True)
		# Appraisal.validate recomputes pms_total_score from the KRA rows, so the
		# fixture score has to be written after the insert, never through it.
		frappe.db.set_value("Appraisal", doc.name, "pms_total_score", score)
		return doc.name

	def _fence_to(self, user: str, company: str) -> None:
		frappe.get_doc(
			{"doctype": "User Permission", "user": user, "allow": "Company", "for_value": company}
		).insert(ignore_permissions=True)

	# --- who is refused ---------------------------------------------------

	def test_plain_employee_is_refused(self):
		frappe.set_user(self.staff_user)
		self.assertFalse(can_view_team_kpi())
		self.assertRaises(frappe.PermissionError, get_team_kpi)

	def test_system_manager_alone_is_refused(self):
		# System Manager is a TECHNICAL role for Desk administration. Holding it
		# must not confer sight of other people's appraisals — the same ruling
		# that keeps it out of HR_SEE_ALL_ROLES everywhere else in this app.
		frappe.get_doc("User", self.staff_user).add_roles("System Manager")
		frappe.set_user(self.staff_user)
		self.assertFalse(can_view_team_kpi())
		self.assertRaises(frappe.PermissionError, get_team_kpi)

	# --- allowlist 1: the CEO, by designation -----------------------------

	def test_ceo_designation_alone_grants_the_view(self):
		frappe.set_user(self.ceo_user)
		self.assertTrue(can_view_team_kpi())

		data = get_team_kpi(year=2026)
		self.assertEqual(data["viewer_mode"], "ceo")
		returned = {row["employee"]: row["total_score"] for row in data["rows"]}
		for employee, score in self.scores.items():
			self.assertEqual(returned.get(employee), score, f"{employee} missing or wrong")

	def test_ceo_holds_the_office_without_any_hr_role(self):
		self.assertFalse(
			set(frappe.get_roles(self.ceo_user)) & {"HR User", "HR Manager", "System Manager"},
			"the CEO fixture must prove DESIGNATION alone is enough",
		)
		frappe.set_user(self.ceo_user)
		self.assertTrue(can_view_team_kpi())

	# --- allowlist 2: HR, by role -----------------------------------------

	def test_hr_role_grants_the_view_without_the_designation(self):
		self.assertNotEqual(frappe.db.get_value("Employee", self.hr, "designation"), CEO_DESIGNATION)
		frappe.set_user(self.hr_user)
		self.assertTrue(can_view_team_kpi())

		data = get_team_kpi(year=2026)
		self.assertEqual(data["viewer_mode"], "hr")
		returned = {row["employee"] for row in data["rows"]}
		self.assertEqual(returned, set(self.scores))

	# --- both see across departments AND companies ------------------------

	def test_both_allowlists_see_every_company(self):
		for user in (self.ceo_user, self.hr_user):
			frappe.set_user(user)
			data = get_team_kpi(year=2026)
			self.assertEqual(
				{self.company, self.other_company},
				set(data["companies"]),
				f"{user} must see both companies",
			)
			self.assertIn(self.far_emp, {row["employee"] for row in data["rows"]})
			self.assertIn(self.far, data["departments"])

	def test_department_filter_narrows_the_rows_and_the_average(self):
		frappe.set_user(self.ceo_user)
		data = get_team_kpi(year=2026, department=self.sales)

		self.assertEqual([row["employee"] for row in data["rows"]], [self.staff])
		self.assertEqual(data["selected_department"], self.sales)
		self.assertAlmostEqual(data["summary"]["average_score"], 90.0)
		self.assertEqual(data["summary"]["headcount"], 1)

	def test_company_filter_narrows_the_rows(self):
		frappe.set_user(self.hr_user)
		data = get_team_kpi(year=2026, company=self.other_company)

		self.assertEqual([row["employee"] for row in data["rows"]], [self.far_emp])
		self.assertEqual(data["selected_company"], self.other_company)
		# the department selector must follow the company, or it offers
		# departments that can never match
		self.assertEqual(data["departments"], [self.far])

	# --- the company fence still binds both --------------------------------

	def test_a_company_user_permission_fences_hr(self):
		self._fence_to(self.hr_user, self.company)
		frappe.set_user(self.hr_user)

		data = get_team_kpi(year=2026)
		self.assertEqual(data["companies"], [self.company])
		self.assertNotIn(self.far_emp, {row["employee"] for row in data["rows"]})

	def test_a_company_user_permission_fences_the_ceo_too(self):
		# One fence, one behaviour: whoever carries a Company User Permission is
		# bounded by it, office or no office.
		self._fence_to(self.ceo_user, self.company)
		frappe.set_user(self.ceo_user)

		data = get_team_kpi(year=2026)
		self.assertEqual(data["companies"], [self.company])
		self.assertNotIn(self.far_emp, {row["employee"] for row in data["rows"]})

	def test_an_appraisal_stamped_with_the_wrong_company_does_not_re_admit_its_owner(self):
		"""Appraisal.company is copied from the Appraisal Cycle and is never
		reconciled with Employee.company — it has no fetch_from and validate()
		does not check it. Fencing on the appraisal therefore leaks: stamp a
		company-B employee's appraisal with company A and a viewer fenced to A
		gets to read them. The fence must key on the EMPLOYEE."""
		frappe.db.set_value("Appraisal", self.appraisals[self.far_emp], "company", self.company)
		self.assertEqual(frappe.db.get_value("Employee", self.far_emp, "company"), self.other_company)

		self._fence_to(self.hr_user, self.company)
		frappe.set_user(self.hr_user)
		data = get_team_kpi(year=2026)

		self.assertNotIn(
			self.far_emp,
			{row["employee"] for row in data["rows"]},
			"an employee outside the fence was re-admitted by their appraisal's company",
		)
		self.assertEqual(data["companies"], [self.company])

	def test_an_appraisal_stamped_with_the_wrong_company_still_shows_its_owner(self):
		"""The mirror of the leak: fencing on the appraisal also HIDES. A
		company-A employee whose appraisal carries company B must still appear
		for a viewer fenced to A — they are an A employee."""
		frappe.db.set_value("Appraisal", self.appraisals[self.staff], "company", self.other_company)

		self._fence_to(self.hr_user, self.company)
		frappe.set_user(self.hr_user)
		data = get_team_kpi(year=2026)

		row = next(r for r in data["rows"] if r["employee"] == self.staff)
		self.assertEqual(row["company"], self.company, "the row's company must be the employee's")

	def test_a_fenced_viewer_cannot_ask_for_a_company_outside_the_fence(self):
		self._fence_to(self.hr_user, self.company)
		frappe.set_user(self.hr_user)
		self.assertRaises(frappe.PermissionError, get_team_kpi, company=self.other_company)

	def test_scores_are_rounded_for_display(self):
		# The ring's centre label prints its score verbatim into an 88px circle
		# with no overflow clamp, and reads it out to a screen reader, so a raw
		# sum/len mean (72.42857142857143) must never leave this endpoint.
		# a second, non-overlapping cycle -> staff averages (90 + 85) / 2 = 87.5
		self._appraisal(self.staff, 85.0, start_date="2026-04-01", end_date="2026-06-30")
		frappe.set_user(self.ceo_user)
		data = get_team_kpi(year=2026)

		staff_row = next(row for row in data["rows"] if row["employee"] == self.staff)
		self.assertEqual(staff_row["total_score"], 87.5)

		for value in [data["summary"]["average_score"], data["summary"]["top_score"]] + [
			row["total_score"] for row in data["rows"]
		]:
			self.assertEqual(round(value, 1), value, f"{value} carries more than one decimal place")

	# --- read-only ---------------------------------------------------------

	def test_view_is_read_only(self):
		# No argument may name something to write, and the module exposes no
		# team-side mutation at all.
		self.assertEqual(
			list(inspect.signature(get_team_kpi).parameters),
			["year", "cycle", "department", "company"],
		)

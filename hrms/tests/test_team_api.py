"""Team endpoint fencing — direct reports only, fail-closed (Phase B, HR letter).

Bench-backed: run with
    bench --site <site> run-tests --module hrms.tests.test_team_api
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api.team import get_managers, get_team_status, has_company_view, has_team

test_dependencies = ["Employee"]


class TestTeamApi(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.manager = make_employee("team_mgr@example.com", company="_Test Company")
		cls.report = make_employee("team_member@example.com", company="_Test Company", reports_to=cls.manager)
		cls.outsider = make_employee("team_outsider@example.com", company="_Test Company")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_manager_sees_only_direct_reports(self):
		frappe.set_user("team_mgr@example.com")
		result = get_team_status()
		names = [m["employee"] for m in result["members"]]
		self.assertIn(self.report, names)
		self.assertNotIn(self.outsider, names)
		self.assertTrue(has_team())

	def test_non_manager_gets_empty_payload_not_error(self):
		frappe.set_user("team_member@example.com")
		result = get_team_status()
		self.assertEqual(result["members"], [])
		self.assertFalse(has_team())

	def test_summary_counts_match_members(self):
		frappe.set_user("team_mgr@example.com")
		result = get_team_status()
		self.assertEqual(sum(result["summary"].values()), len(result["members"]))

	def test_non_hr_cannot_view_another_managers_team(self):
		frappe.set_user("team_member@example.com")
		self.assertRaises(frappe.PermissionError, get_team_status, manager=self.manager)
		self.assertEqual(get_managers(), [])

	def test_system_manager_cannot_browse_teams(self):
		# user rule 2026-08-12: System Manager is not enough to see other teams
		frappe.set_user("Administrator")
		frappe.get_doc("User", "team_member@example.com").add_roles("System Manager")
		frappe.set_user("team_member@example.com")
		self.assertRaises(frappe.PermissionError, get_team_status, manager=self.manager)
		self.assertEqual(get_managers(), [])

	def test_hr_browses_any_team_and_gets_selector_data(self):
		hr_user = frappe.get_doc("User", "team_outsider@example.com")
		hr_user.add_roles("HR User")
		frappe.set_user("team_outsider@example.com")

		self.assertTrue(has_team())  # HR sees the Team entry without reports
		managers = [m["name"] for m in get_managers()]
		self.assertIn(self.manager, managers)

		result = get_team_status(manager=self.manager)
		self.assertEqual(result["manager"], self.manager)
		self.assertIn(self.report, [m["employee"] for m in result["members"]])


class TestAttendanceViewerCompanyTeam(FrappeTestCase):
	"""Owner, 15 Oct 2026: an Attendance Report Viewer (Mia, Shenzhen) sees on Team
	everyone in their Company User Permission, view only, and no Roster."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.colleague = make_employee("viewer_colleague@example.com", company="_Test Company")
		cls.elsewhere = make_employee("viewer_elsewhere@example.com", company="_Test Company 1")
		cls.viewer = make_employee("team_viewer@example.com", company="_Test Company")
		frappe.get_doc("User", "team_viewer@example.com").add_roles("Attendance Report Viewer")

	def tearDown(self):
		frappe.set_user("Administrator")

	def _company_permission(self, company):
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": "team_viewer@example.com",
				"allow": "Company",
				"for_value": company,
			}
		).insert(ignore_permissions=True)

	def test_viewer_sees_everyone_in_their_company_and_no_one_else(self):
		self._company_permission("_Test Company")
		frappe.set_user("team_viewer@example.com")
		result = get_team_status()
		names = [m["employee"] for m in result["members"]]
		self.assertIn(self.colleague, names)
		self.assertNotIn(self.elsewhere, names)
		self.assertTrue(result["company_view"])
		self.assertTrue(has_company_view())
		self.assertFalse(has_team())  # the Roster's gate stays shut

	def test_viewer_without_a_company_permission_sees_nobody(self):
		frappe.set_user("team_viewer@example.com")
		self.assertEqual(get_team_status()["members"], [])

	def test_viewer_cannot_browse_another_managers_team(self):
		self._company_permission("_Test Company")
		frappe.set_user("team_viewer@example.com")
		self.assertRaises(frappe.PermissionError, get_team_status, manager=self.colleague)

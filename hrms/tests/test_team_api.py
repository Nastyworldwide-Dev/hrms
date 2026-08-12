"""Team endpoint fencing — direct reports only, fail-closed (Phase B, HR letter).

Bench-backed: run with
    bench --site <site> run-tests --module hrms.tests.test_team_api
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api.team import get_team_status, has_team

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

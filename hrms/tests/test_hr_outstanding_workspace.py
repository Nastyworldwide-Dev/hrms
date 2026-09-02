# The HR Outstanding workspace is the consolidated "what needs attention"
# surface for HR — every prior Desktop audit found HR had to visit several
# separate reports to know what was unresolved. It aggregates the actionable
# exception reports and links back to the authoritative records; if it silently
# loses a report link or its HR role-gating, that operational visibility is gone
# without anyone noticing. This pins its shape.
import json
import unittest
from pathlib import Path

WS = Path(__file__).resolve().parent.parent / "hr" / "workspace" / "hr_outstanding" / "hr_outstanding.json"

# The exception reports HR needs at month-end / for outstanding work.
EXPECTED_REPORTS = {
	"Out of Radius Activity",
	"Unpaid Expense Claim",
	"Employee Exits",
	"Employees working on a holiday",
}


class TestHROutstandingWorkspace(unittest.TestCase):
	def setUp(self):
		self.ws = json.loads(WS.read_text())

	def test_aggregates_the_exception_reports(self):
		report_links = {
			l["link_to"]
			for l in self.ws["links"]
			if l.get("type") == "Link" and l.get("link_type") == "Report"
		}
		self.assertEqual(
			EXPECTED_REPORTS,
			report_links,
			"the workspace must link exactly the HR exception reports (links back, no duplication)",
		)

	def test_is_gated_to_hr_roles(self):
		roles = {r["role"] for r in self.ws["roles"]}
		self.assertIn("HR User", roles)
		self.assertIn("HR Manager", roles)

	def test_is_a_public_visible_workspace(self):
		self.assertEqual(self.ws["public"], 1)
		self.assertEqual(self.ws.get("is_hidden", 0), 0)


if __name__ == "__main__":
	unittest.main()

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_years, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.leave_rules import auto_assign_leave_policies

COMPANY = "_Test Company"


def make_leave_type_with_slabs(name, slabs):
	if frappe.db.exists("Leave Type", name):
		return name
	doc = frappe.get_doc(
		{
			"doctype": "Leave Type",
			"leave_type_name": name,
			"based_on_years_of_service": 1,
			"include_holiday": 1,
		}
	)
	for from_years, to_years, leave_days in slabs:
		doc.append(
			"service_entitlements",
			{"from_years": from_years, "to_years": to_years, "leave_days": leave_days},
		)
	return doc.insert().name


def make_leave_policy(name, leave_type, annual_allocation):
	existing = frappe.db.exists("Leave Policy", {"title": name})
	if existing:
		return existing
	doc = frappe.get_doc(
		{
			"doctype": "Leave Policy",
			"title": name,
			"leave_policy_details": [{"leave_type": leave_type, "annual_allocation": annual_allocation}],
		}
	).insert()
	doc.submit()
	return doc.name


def make_grade(name, default_leave_policy=None):
	if frappe.db.exists("Employee Grade", name):
		frappe.db.set_value("Employee Grade", name, "default_leave_policy", default_leave_policy)
		return name
	return (
		frappe.get_doc(
			{
				"doctype": "Employee Grade",
				"__newname": name,
				"default_leave_policy": default_leave_policy,
			}
		)
		.insert()
		.name
	)


class TestLeaveRules(FrappeTestCase):
	def setUp(self):
		self.leave_type = make_leave_type_with_slabs("Rule Annual Leave", [(0, 5, 10), (5, 99, 15)])
		self.policy = make_leave_policy("Rule Leave Policy", self.leave_type, 8)
		self.grade = make_grade("Rule Grade", default_leave_policy=self.policy)

		# joined ~6 years ago -> falls in the 5-99 slab (15 days)
		self.employee = make_employee("leave_rule_emp@example.com", company=COMPANY)
		frappe.db.set_value(
			"Employee",
			self.employee,
			{"grade": self.grade, "date_of_joining": add_years(nowdate(), -6)},
		)
		frappe.db.delete("Leave Policy Assignment", {"employee": self.employee})
		frappe.db.delete("Leave Allocation", {"employee": self.employee})
		frappe.db.delete("Leave Ledger Entry", {"employee": self.employee})
		frappe.clear_document_cache("Employee", self.employee)

	def _assignments(self):
		return frappe.get_all(
			"Leave Policy Assignment",
			filters={"employee": self.employee, "docstatus": 1},
			fields=["name", "leave_policy", "effective_from", "effective_to"],
		)

	def test_creates_and_grants_assignment_from_grade_policy(self):
		auto_assign_leave_policies()

		assignments = self._assignments()
		self.assertEqual(len(assignments), 1)
		self.assertEqual(assignments[0].leave_policy, self.policy)

		allocated = frappe.db.get_value(
			"Leave Allocation",
			{"employee": self.employee, "leave_type": self.leave_type, "docstatus": 1},
			"total_leaves_allocated",
		)
		# slab (5-99 yrs -> 15) overrides the policy's annual_allocation of 8
		self.assertEqual(int(allocated), 15)

	def test_job_is_idempotent(self):
		auto_assign_leave_policies()
		auto_assign_leave_policies()
		self.assertEqual(len(self._assignments()), 1)

	def test_skips_employee_whose_grade_has_no_policy(self):
		grade = make_grade("Rule Grade No Policy")
		frappe.db.set_value("Employee", self.employee, "grade", grade)
		frappe.clear_document_cache("Employee", self.employee)

		auto_assign_leave_policies()
		self.assertEqual(self._assignments(), [])

	def test_skips_inactive_employee(self):
		frappe.db.set_value("Employee", self.employee, "status", "Left")
		frappe.clear_document_cache("Employee", self.employee)

		auto_assign_leave_policies()
		self.assertEqual(self._assignments(), [])

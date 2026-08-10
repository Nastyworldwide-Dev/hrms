import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, getdate

from hrms.hr.doctype.leave_application.test_leave_application import get_employee
from hrms.hr.doctype.leave_period.test_leave_period import create_leave_period
from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import (
	LeavePolicyAssignment,
	create_assignment_for_multiple_employees,
)
from hrms.overrides.leave_policy_assignment_override import CustomLeavePolicyAssignment
from hrms.patches.v15_92_0.add_leave_type_do_not_prorate_field import (
	execute as add_do_not_prorate_field,
)

test_dependencies = ["Employee"]

PERIOD_START = "2026-01-01"
PERIOD_END = "2026-12-31"
# 184 remaining days of 365 → 14 * 184/365 = 7.06 → rounds to 7
MID_YEAR_DOJ = "2026-07-01"


def make_leave_type(name, **kwargs):
	if frappe.db.exists("Leave Type", name):
		frappe.delete_doc("Leave Type", name, force=True)
	return (
		frappe.get_doc(
			{
				"doctype": "Leave Type",
				"leave_type_name": name,
				"include_holiday": 1,
				**kwargs,
			}
		)
		.insert()
		.name
	)


def make_policy(title, details):
	policy = frappe.get_doc(
		{
			"doctype": "Leave Policy",
			"title": title,
			"leave_policy_details": [
				{"leave_type": leave_type, "annual_allocation": days} for leave_type, days in details
			],
		}
	).insert()
	policy.submit()
	return policy


class TestDoNotProrateOnPolicyAssignment(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# fresh sites mark patches as completed without executing them,
		# so install the custom field explicitly (idempotent)
		add_do_not_prorate_field()

	def setUp(self):
		for doctype in [
			"Leave Period",
			"Leave Application",
			"Leave Allocation",
			"Leave Policy",
			"Leave Policy Assignment",
			"Leave Ledger Entry",
		]:
			frappe.db.delete(doctype)

		self.employee = get_employee()
		self.original_doj = self.employee.date_of_joining
		self.leave_period = create_leave_period(PERIOD_START, PERIOD_END, "_Test Company")
		self.annual = make_leave_type("_Test Prorated Annual Leave")
		self.medical = make_leave_type("_Test No Prorate Medical Leave", custom_do_not_prorate=1)
		self.hospitalization = make_leave_type(
			"_Test No Prorate Hospitalization Leave", custom_do_not_prorate=1
		)
		self.policy = make_policy(
			"Test Do Not Prorate Policy",
			[(self.annual, 14), (self.medical, 14), (self.hospitalization, 60)],
		)

	def tearDown(self):
		frappe.db.set_value("Employee", self.employee.name, "date_of_joining", self.original_doj)

	def set_doj(self, date):
		frappe.db.set_value("Employee", self.employee.name, "date_of_joining", date)

	def submit_assignment(self):
		assignment = frappe.get_doc(
			{
				"doctype": "Leave Policy Assignment",
				"employee": self.employee.name,
				"assignment_based_on": "Leave Period",
				"leave_policy": self.policy.name,
				"leave_period": self.leave_period.name,
			}
		).insert()
		assignment.submit()
		return assignment

	def get_allocated(self, assignment_name):
		return {
			d.leave_type: flt(d.new_leaves_allocated)
			for d in frappe.get_all(
				"Leave Allocation",
				filters={"leave_policy_assignment": assignment_name, "docstatus": 1},
				fields=["leave_type", "new_leaves_allocated"],
			)
		}

	def test_override_class_is_wired(self):
		self.assertIsInstance(frappe.new_doc("Leave Policy Assignment"), CustomLeavePolicyAssignment)

	def test_should_skip_proration_guard(self):
		doc = frappe.new_doc("Leave Policy Assignment")
		flagged = frappe._dict(name=self.medical, is_earned_leave=0, is_compensatory=0)
		unflagged = frappe._dict(name=self.annual, is_earned_leave=0, is_compensatory=0)
		earned_flagged = frappe._dict(name=self.medical, is_earned_leave=1, is_compensatory=0)
		compensatory_flagged = frappe._dict(name=self.medical, is_earned_leave=0, is_compensatory=1)
		self.assertTrue(doc.should_skip_proration(flagged))
		self.assertFalse(doc.should_skip_proration(unflagged))
		self.assertFalse(doc.should_skip_proration(earned_flagged))
		self.assertFalse(doc.should_skip_proration(compensatory_flagged))

	def test_mid_period_joiner_prorates_only_unflagged_types(self):
		self.set_doj(MID_YEAR_DOJ)
		assignment = self.submit_assignment()
		allocated = self.get_allocated(assignment.name)
		self.assertEqual(allocated[self.annual], 7.0)
		self.assertEqual(allocated[self.medical], 14.0)
		self.assertEqual(allocated[self.hospitalization], 60.0)

	def test_bulk_assignment_path_matches_single_path(self):
		self.set_doj(MID_YEAR_DOJ)
		created = create_assignment_for_multiple_employees(
			[self.employee.name],
			frappe._dict(
				assignment_based_on="Leave Period",
				leave_policy=self.policy.name,
				leave_period=self.leave_period.name,
				carry_forward=0,
			),
		)
		allocated = self.get_allocated(created[0])
		self.assertEqual(allocated[self.annual], 7.0)
		self.assertEqual(allocated[self.medical], 14.0)
		self.assertEqual(allocated[self.hospitalization], 60.0)

	def test_doj_before_period_start_keeps_full_allocation_for_all(self):
		self.set_doj("2025-06-01")
		assignment = self.submit_assignment()
		allocated = self.get_allocated(assignment.name)
		self.assertEqual(allocated[self.annual], 14.0)
		self.assertEqual(allocated[self.medical], 14.0)
		self.assertEqual(allocated[self.hospitalization], 60.0)

	def test_joining_date_assignment_unchanged(self):
		self.set_doj(MID_YEAR_DOJ)
		assignment = frappe.get_doc(
			{
				"doctype": "Leave Policy Assignment",
				"employee": self.employee.name,
				"assignment_based_on": "Joining Date",
				"leave_policy": self.policy.name,
			}
		).insert()
		assignment.submit()
		allocated = self.get_allocated(assignment.name)
		# effective_from == DOJ, so nothing is prorated today — must stay that way
		self.assertEqual(allocated[self.annual], 14.0)
		self.assertEqual(allocated[self.medical], 14.0)
		self.assertEqual(allocated[self.hospitalization], 60.0)

	def test_flagged_earned_leave_keeps_stock_behavior(self):
		earned = make_leave_type(
			"_Test No Prorate Earned Leave",
			is_earned_leave=1,
			earned_leave_frequency="Monthly",
			allocate_on_day="First Day",
			rounding="0.5",
			custom_do_not_prorate=1,
		)
		self.set_doj(MID_YEAR_DOJ)
		policy = make_policy("Test Do Not Prorate Earned Policy", [(earned, 12)])
		assignment = frappe.get_doc(
			{
				"doctype": "Leave Policy Assignment",
				"employee": self.employee.name,
				"assignment_based_on": "Leave Period",
				"leave_policy": policy.name,
				"leave_period": self.leave_period.name,
			}
		).insert()

		leave_details = frappe.db.get_value(
			"Leave Type",
			earned,
			[
				"name",
				"is_earned_leave",
				"is_compensatory",
				"earned_leave_frequency",
				"allocate_on_day",
				"rounding",
			],
			as_dict=True,
		)
		doj = getdate(MID_YEAR_DOJ)
		stock = LeavePolicyAssignment.get_new_leaves(assignment, 12, leave_details, doj)
		actual = assignment.get_new_leaves(12, leave_details, doj)
		# the checkbox is ignored for earned leaves: accrual math is untouched
		self.assertEqual(actual, stock)
		self.assertNotEqual(actual, 12)

	def test_no_double_allocation_on_regrant_or_reassign(self):
		self.set_doj(MID_YEAR_DOJ)
		assignment = self.submit_assignment()

		# re-granting the same assignment must throw, not allocate twice
		self.assertRaises(frappe.ValidationError, assignment.grant_leave_alloc_for_employee)

		# an overlapping second assignment is rejected outright
		overlapping = frappe.get_doc(
			{
				"doctype": "Leave Policy Assignment",
				"employee": self.employee.name,
				"assignment_based_on": "Leave Period",
				"leave_policy": self.policy.name,
				"leave_period": self.leave_period.name,
			}
		).insert()
		self.assertRaises(frappe.ValidationError, overlapping.submit)
		overlapping.delete()

		# cancel + re-assign → exactly one submitted allocation per type, same amounts
		for name in frappe.get_all(
			"Leave Allocation", filters={"leave_policy_assignment": assignment.name}, pluck="name"
		):
			frappe.get_doc("Leave Allocation", name).cancel()
		assignment.reload()
		assignment.cancel()

		reassigned = self.submit_assignment()
		allocations = frappe.get_all(
			"Leave Allocation",
			filters={"employee": self.employee.name, "docstatus": 1},
			fields=["leave_type", "new_leaves_allocated"],
		)
		self.assertEqual(len(allocations), 3)
		allocated = self.get_allocated(reassigned.name)
		self.assertEqual(allocated[self.annual], 7.0)
		self.assertEqual(allocated[self.medical], 14.0)
		self.assertEqual(allocated[self.hospitalization], 60.0)

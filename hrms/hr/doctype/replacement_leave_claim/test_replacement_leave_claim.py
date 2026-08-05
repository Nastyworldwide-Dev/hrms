# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, get_year_ending, get_year_start, getdate, today

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.leave_period.test_leave_period import create_leave_period
from hrms.hr.doctype.ot_request.test_ot_request import (
	attach_supporting_file,
	make_ot_checkins,
	make_ot_request,
)
from hrms.utils.test_ot_calculation import create_shift_type

test_dependencies = ["Employee"]

SHIFT = "_Test RLC Shift"


def make_claim(employee, claimed_days, submit=True):
	claim = frappe.get_doc(
		{
			"doctype": "Replacement Leave Claim",
			"employee": employee,
			"claimed_days": claimed_days,
			"company": "_Test Company",
		}
	).insert()
	if submit:
		attach_supporting_file(claim)
		claim.submit()
	return claim


class TestReplacementLeaveClaim(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_shift_type(
			SHIFT,
			enable_overtime=1,
			minimum_overtime_minutes=0,
			allow_check_out_after_shift_end_time=120,
		)
		cls.employee = make_employee("rlc_emp@example.com", company="_Test Company")

	def setUp(self):
		for doctype in ("Replacement Leave Claim", "OT Request", "Employee Checkin"):
			frappe.db.delete(doctype)
		frappe.db.delete("Leave Allocation", {"leave_type": "Replacement Leave"})
		frappe.db.delete("Leave Ledger Entry", {"leave_type": "Replacement Leave"})
		if not frappe.db.exists("Leave Type", "Replacement Leave"):
			frappe.get_doc({"doctype": "Leave Type", "leave_type_name": "Replacement Leave"}).insert()
		if not frappe.db.exists(
			"Leave Period",
			{"company": "_Test Company", "from_date": ("<=", today()), "to_date": (">=", today())},
		):
			create_leave_period(get_year_start(getdate()), get_year_ending(getdate()), "_Test Company")
		frappe.db.set_value("Employee", self.employee, "eligible_for_overtime_pay", 0)

	def bank_hours(self):
		"""Approve 8 replacement-leave OT hours today: shift bounds put the
		real shift end at 10:00 (12:00 actual - 120min buffer), so an 18:00
		check-out proves 8 whole hours."""
		make_ot_checkins(self.employee, today(), shift=SHIFT, out_time="18:00:00", actual_end="12:00:00")
		make_ot_request(self.employee, claimed_hours=8)

	def test_half_day_step_validation(self):
		self.bank_hours()
		self.assertRaises(frappe.ValidationError, make_claim, self.employee, 0.3, False)
		self.assertRaises(frappe.ValidationError, make_claim, self.employee, 0, False)

	def test_claim_above_bank_rejected(self):
		self.bank_hours()
		self.assertRaises(frappe.ValidationError, make_claim, self.employee, 2.0, False)

	def test_approval_adds_days_to_allocation(self):
		self.bank_hours()
		claim = make_claim(self.employee, 1.0)
		self.assertTrue(claim.leave_allocation)
		allocation = frappe.get_doc("Leave Allocation", claim.leave_allocation)
		self.assertEqual(allocation.leave_type, "Replacement Leave")
		self.assertEqual(allocation.total_leaves_allocated, 1.0)

	def test_second_claim_tops_up_same_allocation(self):
		self.bank_hours()
		first = make_claim(self.employee, 0.5)
		second = make_claim(self.employee, 0.5)
		self.assertEqual(first.leave_allocation, second.leave_allocation)
		allocation = frappe.get_doc("Leave Allocation", first.leave_allocation)
		self.assertEqual(allocation.total_leaves_allocated, 1.0)

	def test_cancel_reverses_allocation(self):
		self.bank_hours()
		claim = make_claim(self.employee, 1.0)
		claim.cancel()
		allocation = frappe.get_doc("Leave Allocation", claim.leave_allocation)
		self.assertEqual(allocation.total_leaves_allocated, 0)

	def test_pending_claim_reserves_bank_hours(self):
		self.bank_hours()
		make_claim(self.employee, 1.0, submit=False)  # draft reserves 8h
		self.assertRaises(frappe.ValidationError, make_claim, self.employee, 1.0, False)

	def test_ot_cancel_blocked_when_hours_claimed(self):
		self.bank_hours()
		make_claim(self.employee, 1.0)
		ot_request = frappe.get_doc(
			"OT Request", {"employee": self.employee, "claimed_hours": 8, "docstatus": 1}
		)
		self.assertRaises(frappe.ValidationError, ot_request.cancel)

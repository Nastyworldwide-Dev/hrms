"""Regression tests for hrms.hr.shift_rules (the location/department Shift
Assignment rule layer). Co-located with the module it exercises; reuses the
Shift Location fixtures from the doctype test module so nothing is duplicated.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.shift_location.test_shift_rules import make_department, make_shift_location
from hrms.hr.doctype.shift_type.test_shift_type import setup_shift_type
from hrms.hr.shift_rules import reconcile_employee_shift

COMPANY = "_Test Company"


class TestShiftRulesRosterPrecedence(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Shift Assignment")
		self.shift_day = setup_shift_type(shift_type="Rule Shift Day")
		self.shift_night = setup_shift_type(
			shift_type="Rule Shift Night", start_time="19:00:00", end_time="03:30:00"
		)
		self.warehouse = make_department("Rule Warehouse")  # no rule dept -> site default
		# site default rule = night
		self.location = make_shift_location("Rule Loc HQ", [{"shift_type": self.shift_night.name}])
		self.employee = make_employee("shift_rule_roster_emp@example.com", company=COMPANY)
		self._set_employee(department=self.warehouse, shift_location=self.location)

	def _set_employee(self, **values):
		for field, value in values.items():
			frappe.db.set_value("Employee", self.employee, field, value)
		frappe.clear_document_cache("Employee", self.employee)

	def _make_manual(self, start_off, end_off):
		frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"employee": self.employee,
				"company": COMPANY,
				"shift_type": self.shift_day.name,
				"start_date": add_days(nowdate(), start_off),
				"end_date": add_days(nowdate(), end_off),
				"status": "Active",
			}
		).insert().submit()

	def _autos(self):
		return frappe.get_all(
			"Shift Assignment",
			filters={
				"employee": self.employee,
				"docstatus": 1,
				"status": "Active",
				"created_by_shift_rule": 1,
			},
			pluck="name",
		)

	def test_lapsed_manual_roster_blocks_rule_takeover(self):
		"""The real defect: a variable-shift employee's manual roster segment
		ended yesterday, so the rule layer imposed the open-ended site-default
		(night) shift into the gap — "the system changed her to the night shift
		mid-month, until end of month". A non-rule assignment that ended within
		one roster cycle must keep the rule layer standing down."""
		self._make_manual(-7, -1)  # ended yesterday
		self.assertEqual(reconcile_employee_shift(self.employee), "skipped-manual")
		self.assertEqual(self._autos(), [])

	def test_unmanaged_employee_still_rule_managed(self):
		# No manual history at all: the rule layer must still provide a shift.
		self.assertEqual(reconcile_employee_shift(self.employee), "created")
		self.assertEqual(len(self._autos()), 1)

	def test_stale_manual_beyond_window_hands_off_to_rule(self):
		# A roster segment that ended well beyond one cycle is a genuine lapse;
		# the rule layer legitimately takes over.
		self._make_manual(-50, -40)
		self.assertEqual(reconcile_employee_shift(self.employee), "created")
		self.assertEqual(len(self._autos()), 1)

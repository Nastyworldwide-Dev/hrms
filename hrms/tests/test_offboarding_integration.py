"""Bench integration coverage for `hrms.hr.offboarding`.

The bench-free suite (test_offboarding.py) proves the policy math against
fakes; this suite proves the wiring against the REAL controllers: an
Employee save must drive Leave Allocation's own on_update_after_submit
path (ledger delta included), and the status sweep must flip a real
Employee document. Needs a bench:

    bench --site <site> run-tests --app hrms --module hrms.tests.test_offboarding_integration
"""

import frappe
from frappe.utils import add_days, nowdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.leave_type.test_leave_type import create_leave_type
from hrms.hr.offboarding import update_relieved_employee_status
from hrms.tests.utils import HRMSTestSuite

LEAVE_TYPE = "_Test Offboarding Leave"


class TestOffboardingIntegration(HRMSTestSuite):
	def setUp(self):
		emp_id = make_employee("test_offboarding_integration@example.com", company="_Test Company")
		self.employee = frappe.get_doc("Employee", emp_id)
		self._reset_employee()
		create_leave_type(leave_type_name=LEAVE_TYPE)

	def tearDown(self):
		self._reset_employee()

	def _reset_employee(self):
		for row in frappe.get_all(
			"Leave Allocation", filters={"employee": self.employee.name, "docstatus": ["<", 2]}
		):
			allocation = frappe.get_doc("Leave Allocation", row.name)
			if allocation.docstatus == 1:
				allocation.cancel()
			allocation.delete()
		frappe.db.set_value("Employee", self.employee.name, {"relieving_date": None, "status": "Active"})
		self.employee.reload()

	def _make_allocation(self):
		allocation = frappe.get_doc(
			{
				"doctype": "Leave Allocation",
				"employee": self.employee.name,
				"employee_name": self.employee.employee_name,
				"leave_type": LEAVE_TYPE,
				"from_date": "2030-01-01",
				"to_date": "2030-12-31",
				"new_leaves_allocated": 30,
			}
		)
		allocation.insert()
		allocation.submit()
		return allocation

	def _set_relieving_date(self, value):
		self.employee.reload()
		self.employee.relieving_date = value
		self.employee.save()

	def test_relieving_date_prorates_ledger_and_restores(self):
		allocation = self._make_allocation()

		# Jan 1 .. Jun 30 2030 = 181 of 365 days -> 30 * 181/365 -> 15
		self._set_relieving_date("2030-06-30")
		allocation.reload()
		self.assertEqual(allocation.new_leaves_allocated, 15)
		self.assertEqual(allocation.pre_offboarding_leaves, 30)
		self.assertEqual(allocation.total_leaves_allocated, 15)
		self.assertEqual(self._ledger_balance(allocation), 15)

		# re-saving the employee without a change is a no-op
		self.employee.reload()
		self.employee.save()
		allocation.reload()
		self.assertEqual(allocation.new_leaves_allocated, 15)

		# moving the date reprorates from the parked baseline, not from 15
		self._set_relieving_date("2030-09-30")
		allocation.reload()
		self.assertEqual(allocation.new_leaves_allocated, 22)
		self.assertEqual(allocation.pre_offboarding_leaves, 30)

		# cancelling the offboarding restores the original entitlement
		self._set_relieving_date(None)
		allocation.reload()
		self.assertEqual(allocation.new_leaves_allocated, 30)
		self.assertEqual(allocation.pre_offboarding_leaves, 0)
		self.assertEqual(self._ledger_balance(allocation), 30)

	def _ledger_balance(self, allocation):
		rows = frappe.get_all(
			"Leave Ledger Entry",
			filters={"transaction_name": allocation.name, "docstatus": 1},
			fields=["leaves"],
		)
		return sum(row.leaves for row in rows)

	def test_status_sweep_marks_left_and_is_rerun_safe(self):
		self.employee.relieving_date = add_days(nowdate(), -30)
		self.employee.save()

		counters = update_relieved_employee_status(employee=self.employee.name)
		self.assertEqual(counters["marked_left"], 1)
		self.employee.reload()
		self.assertEqual(self.employee.status, "Left")

		# rerun: the employee no longer matches the criteria, nothing happens
		counters = update_relieved_employee_status(employee=self.employee.name)
		self.assertEqual(counters, {"marked_left": 0, "waiting": 0, "blocked": 0, "error": 0})

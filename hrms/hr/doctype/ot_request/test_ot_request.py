# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_months, get_datetime, getdate, today

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.ot_request.ot_request import get_replacement_leave_bank
from hrms.utils.ot_calculation import get_ot_pay
from hrms.utils.test_ot_calculation import create_shift_type

test_dependencies = ["Employee"]

SHIFT = "_Test OTR Shift"


def make_ot_checkins(
	employee, date, shift=SHIFT, in_time="09:00:00", out_time="21:12:00", actual_end="20:00:00"
):
	"""Raw IN/OUT rows carrying their own shift bounds (bypasses shift
	resolution — the OT scan reads these fields off the row). The real shift
	end is actual_end minus the shift's 120min checkout buffer."""
	rows = []
	for log_type, time in (("IN", in_time), ("OUT", out_time)):
		doc = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee,
				"log_type": log_type,
				"time": get_datetime(f"{date} {time}"),
				"shift": shift,
				"shift_actual_start": get_datetime(f"{date} 08:00:00"),
				"shift_actual_end": get_datetime(f"{date} {actual_end}"),
			}
		)
		doc.name = f"TEST-CKIN-{employee}-{date}-{log_type}"
		doc.db_insert()
		rows.append(doc.name)
	return rows


def attach_supporting_file(doc):
	frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"supporting-{doc.name}.txt",
			"content": "supporting document",
			"attached_to_doctype": doc.doctype,
			"attached_to_name": doc.name,
		}
	).insert(ignore_permissions=True)


def make_ot_request(employee, ot_date=None, claimed_hours=3, submit=True, **args):
	request = frappe.get_doc(
		{
			"doctype": "OT Request",
			"employee": employee,
			"ot_date": ot_date or today(),
			"claimed_hours": claimed_hours,
			"company": "_Test Company",
			**args,
		}
	).insert()
	if submit:
		attach_supporting_file(request)
		request.submit()
	return request


class TestOTRequest(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# 9-6 shift, OT enabled, 2h checkout buffer -> real shift end 18:00
		create_shift_type(
			SHIFT,
			enable_overtime=1,
			minimum_overtime_minutes=0,
			allow_check_out_after_shift_end_time=120,
		)
		cls.employee = make_employee("otr_emp@example.com", company="_Test Company")

	def setUp(self):
		for doctype in ("OT Request", "Replacement Leave Claim", "Employee Checkin"):
			frappe.db.delete(doctype)
		frappe.db.set_value("Employee", self.employee, "eligible_for_overtime_pay", 0)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_punch_cap_floors_to_whole_hours(self):
		# out 21:12 vs real end 18:00 = 3.2h punched -> cap 3
		make_ot_checkins(self.employee, today())
		request = make_ot_request(self.employee, claimed_hours=3, submit=False)
		self.assertEqual(request.punch_ot_hours, 3)

	def test_claim_above_punch_cap_rejected(self):
		make_ot_checkins(self.employee, today())
		self.assertRaises(
			frappe.ValidationError, make_ot_request, self.employee, claimed_hours=4, submit=False
		)

	def test_no_punches_means_nothing_claimable(self):
		self.assertRaises(
			frappe.ValidationError, make_ot_request, self.employee, claimed_hours=1, submit=False
		)

	def test_out_of_month_filing_rejected(self):
		last_month = add_months(getdate(), -1)
		make_ot_checkins(self.employee, last_month)
		self.assertRaises(
			frappe.ValidationError,
			make_ot_request,
			self.employee,
			ot_date=last_month,
			claimed_hours=1,
			submit=False,
		)

	def test_compensation_forced_by_employee_flag(self):
		make_ot_checkins(self.employee, today())
		request = make_ot_request(self.employee, submit=False, compensation="Overtime Pay")
		# flag off -> replacement leave, whatever the client sent
		self.assertEqual(request.compensation, "Replacement Leave")

		frappe.db.set_value("Employee", self.employee, "eligible_for_overtime_pay", 1)
		request.save()
		self.assertEqual(request.compensation, "Overtime Pay")

	def test_duplicate_day_rejected(self):
		make_ot_checkins(self.employee, today())
		make_ot_request(self.employee, submit=False)
		self.assertRaises(
			frappe.ValidationError, make_ot_request, self.employee, claimed_hours=1, submit=False
		)

	def test_submit_needs_attachment(self):
		make_ot_checkins(self.employee, today())
		request = make_ot_request(self.employee, submit=False)
		self.assertRaises(frappe.ValidationError, request.submit)

	def test_self_submission_blocked(self):
		from frappe.utils.user import add_role

		make_ot_checkins(self.employee, today())
		request = make_ot_request(self.employee, submit=False)
		attach_supporting_file(request)

		user = frappe.db.get_value("Employee", self.employee, "user_id")
		add_role(user, "System Manager")
		self.addCleanup(lambda: frappe.get_doc("User", user).remove_roles("System Manager"))
		frappe.set_user(user)
		self.assertRaises(frappe.ValidationError, request.submit)

	def test_filing_for_colleague_blocked(self):
		colleague = make_employee("otr_colleague@example.com", company="_Test Company")
		make_ot_checkins(colleague, today())
		frappe.set_user(frappe.db.get_value("Employee", self.employee, "user_id"))
		self.assertRaises(frappe.PermissionError, make_ot_request, colleague, claimed_hours=1, submit=False)

	def test_ot_pay_priced_only_when_approved(self):
		frappe.db.set_value("Employee", self.employee, "eligible_for_overtime_pay", 1)
		make_ot_checkins(self.employee, today())
		# hourly rate = 4160 / (26*8) = 20; normal-day band 1.5x

		# punches alone price nothing
		self.assertEqual(get_ot_pay(self.employee, today(), today(), 4160), 0.0)

		# approved request for 2 of the 3 punched hours -> 2 * 20 * 1.5 = 60
		make_ot_request(self.employee, claimed_hours=2)
		self.assertEqual(get_ot_pay(self.employee, today(), today(), 4160), 60.0)

	def test_replacement_leave_bank(self):
		make_ot_checkins(self.employee, today())
		make_ot_request(self.employee, claimed_hours=3)
		bank = get_replacement_leave_bank(self.employee, getdate())
		self.assertEqual(bank["hours_total"], 3)
		self.assertEqual(bank["hours_claimed"], 0)
		self.assertEqual(bank["hours_available"], 3)

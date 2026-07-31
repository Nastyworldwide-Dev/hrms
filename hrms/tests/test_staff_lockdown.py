# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime, time_diff_in_seconds

from erpnext.setup.doctype.employee.test_employee import make_employee

import hrms.api
from hrms.api.remote_checkin import punch
from hrms.hr.doctype.employee_checkin.employee_checkin import add_log_based_on_employee_field

STAFF_DIRECTORY_FIELDS = {"name", "employee_name", "designation", "department", "image"}


class TestStaffLockdown(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.manager_user = "staff-lockdown-manager@example.com"
		cls.staff_user = "staff-lockdown-staff@example.com"
		cls.friend_user = "staff-lockdown-friend@example.com"
		cls.manager = make_employee(cls.manager_user, company="_Test Company")
		cls.staff = make_employee(cls.staff_user, company="_Test Company", reports_to=cls.manager)
		cls.friend = make_employee(cls.friend_user, company="_Test Company")

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def _new_leave_application(self, approver):
		return frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": self.staff,
				"leave_type": "_Test Leave Type",
				"from_date": now_datetime().date(),
				"to_date": now_datetime().date(),
				"leave_approver": approver,
				"status": "Open",
			}
		)

	# --- approver fence -------------------------------------------------

	def test_staff_can_route_to_reporting_manager(self):
		frappe.set_user(self.staff_user)
		doc = self._new_leave_application(self.manager_user)
		doc.validate_staff_approver()  # must not raise

	def test_staff_cannot_route_to_arbitrary_user(self):
		frappe.set_user(self.staff_user)
		doc = self._new_leave_application(self.friend_user)
		self.assertRaises(frappe.ValidationError, doc.validate_staff_approver)

	def test_staff_cannot_route_to_self(self):
		frappe.set_user(self.staff_user)
		doc = self._new_leave_application(self.staff_user)
		self.assertRaises(frappe.ValidationError, doc.validate_staff_approver)

	def test_hr_exempt_from_approver_fence(self):
		hr_user = "staff-lockdown-hr@example.com"
		make_employee(hr_user, company="_Test Company")
		user = frappe.get_doc("User", hr_user)
		user.add_roles("HR User")
		frappe.set_user(hr_user)
		doc = self._new_leave_application(self.friend_user)
		doc.validate_staff_approver()  # must not raise

	def test_explicit_leave_approver_field_is_allowed(self):
		frappe.db.set_value("Employee", self.staff, "leave_approver", self.friend_user)
		self.addCleanup(frappe.db.set_value, "Employee", self.staff, "leave_approver", "")
		frappe.set_user(self.staff_user)
		doc = self._new_leave_application(self.friend_user)
		doc.validate_staff_approver()  # must not raise

	# --- PWA punch endpoint ---------------------------------------------

	def test_punch_creates_own_checkin_on_server_clock(self):
		frappe.set_user(self.staff_user)
		doc = punch(
			employee=self.staff,
			log_type="IN",
			latitude=3.139,
			longitude=101.6869,
			time="2020-01-01 08:59:00",  # forged client time must be ignored
		)
		self.assertEqual(doc.employee, self.staff)
		self.assertLessEqual(abs(time_diff_in_seconds(now_datetime(), doc.time)), 10)

	def test_punch_rejects_other_employee(self):
		frappe.set_user(self.staff_user)
		self.assertRaises(frappe.PermissionError, punch, employee=self.friend, log_type="IN")

	def test_punch_rejects_invalid_log_type(self):
		frappe.set_user(self.staff_user)
		self.assertRaises(frappe.ValidationError, punch, employee=self.staff, log_type="LUNCH")

	# --- desk / integration surfaces ------------------------------------

	def test_staff_cannot_create_checkin_via_desk(self):
		frappe.set_user(self.staff_user)
		self.assertFalse(frappe.has_permission("Employee Checkin", "create"))
		self.assertFalse(frappe.has_permission("Employee Checkin", "write"))
		self.assertFalse(frappe.has_permission("Employee Checkin", "delete"))
		self.assertTrue(frappe.has_permission("Employee Checkin", "read"))

	def test_staff_cannot_forge_punch_via_device_endpoint(self):
		frappe.db.set_value("Employee", self.staff, "attendance_device_id", "LOCKDOWN-1")
		self.addCleanup(frappe.db.set_value, "Employee", self.staff, "attendance_device_id", "")
		frappe.set_user(self.staff_user)
		self.assertRaises(
			frappe.PermissionError,
			add_log_based_on_employee_field,
			employee_field_value="LOCKDOWN-1",
			timestamp="2026-07-31 08:59:00",
		)

	def test_download_salary_slip_endpoint_removed(self):
		self.assertFalse(hasattr(hrms.api, "download_salary_slip"))

	def test_directory_minimal_fields_for_staff(self):
		frappe.set_user(self.staff_user)
		rows = hrms.api.get_all_employees()
		self.assertTrue(rows)
		for row in rows:
			leaked = set(row.keys()) - STAFF_DIRECTORY_FIELDS
			self.assertFalse(leaked, f"staff directory leaks fields: {leaked}")

	def test_directory_full_fields_for_hr(self):
		rows = hrms.api.get_all_employees()  # Administrator
		self.assertTrue(rows)
		self.assertIn("user_id", rows[0])

	# --- patch behaviour on a custom-perm site ---------------------------

	def test_patch_keeps_staff_read_when_custom_perms_exist(self):
		"""Any Custom DocPerm row makes a doctype's JSON perms inert — the patch
		must restore staff level-0 read or the PWA leave flow breaks."""
		from frappe.permissions import setup_custom_perms

		from hrms.patches.v15_99_0.staff_perm_lockdown import execute

		for doctype in ("Leave Type", "Shift Type"):
			setup_custom_perms(doctype)
		self.assertTrue(frappe.db.exists("Custom DocPerm", {"parent": "Leave Type"}))

		execute()
		frappe.clear_cache()

		frappe.set_user(self.staff_user)
		for doctype in ("Leave Type", "Shift Type"):
			self.assertTrue(
				frappe.has_permission(doctype, "read"),
				f"staff lost read on {doctype} after patch",
			)
			self.assertFalse(frappe.has_permission(doctype, "write"))

	def test_patch_is_idempotent(self):
		from hrms.patches.v15_99_0.staff_perm_lockdown import execute

		execute()
		execute()  # must not raise
		self.assertTrue(frappe.db.get_single_value("HR Settings", "prevent_self_leave_approval"))
		self.assertTrue(frappe.db.get_single_value("HR Settings", "prevent_self_expense_approval"))

	def test_staff_cannot_file_request_for_another_employee(self):
		frappe.set_user(self.staff_user)
		doc = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": self.friend,
				"leave_type": "_Test Leave Type",
				"from_date": now_datetime().date(),
				"to_date": now_datetime().date(),
				"leave_approver": self.manager_user,
				"status": "Open",
			}
		)
		self.assertRaises(frappe.PermissionError, doc.validate_staff_approver)

	def test_attendance_calendar_scoped_to_own_employee(self):
		frappe.set_user(self.staff_user)
		self.assertRaises(
			frappe.PermissionError,
			hrms.api.get_attendance_calendar_events,
			employee=self.friend,
			from_date="2026-07-01",
			to_date="2026-07-31",
		)
		# own calendar stays accessible
		hrms.api.get_attendance_calendar_events(
			employee=self.staff, from_date="2026-07-01", to_date="2026-07-31"
		)

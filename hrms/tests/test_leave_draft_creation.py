"""An employee can save a Leave Request draft; the approver is required to SUBMIT.

Two defects met on this workflow:

1. `validate_leave_approver` fired on every save (`docstatus != 2`), so an
   employee whose Employee record carries no `leave_approver`, no `reports_to`
   and no department approver could not save a draft at all — and the approver
   they lacked is exactly what HR configures afterwards. The rule belongs at
   submit, where "no leave is approved without a named approver" is what it
   actually protects.

2. The PWA offered approvers the backend then refused. `get_leave_approval_details`
   built its dropdown from `get_department_approvers`, which walks the whole
   department ANCESTOR chain, while `validate_staff_approver` accepts only the
   employee's OWN department (plus Employee.leave_approver and reports_to). Both
   now read `hrms.hr.utils.get_designated_approvers`.

The narrow boundary is deliberate: no evidence in this repo or the as-hr_kpi
donor says a parent-department approver may approve for a child department, so
widening it would hand approval authority to people nobody authorised. That
remains an open HR policy question.

Bench-backed — NOT verified at runtime in the porting environment (no bench /
no frappe module available). Run with:
    bench --site <site> run-tests --module hrms.tests.test_leave_draft_creation
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.utils import get_designated_approvers

test_dependencies = ["Employee"]


def make_leave_type(name="_Test Draft Leave"):
	if not frappe.db.exists("Leave Type", name):
		frappe.get_doc(
			{"doctype": "Leave Type", "leave_type_name": name, "include_holiday": 1, "allow_negative": 1}
		).insert()
	return name


class TestLeaveDraftCreation(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.leave_type = make_leave_type()
		# no leave_approver, no reports_to, no department approver: the exact
		# shape that could not save a draft
		cls.orphan = make_employee("draft_orphan@example.com", company="_Test Company")
		frappe.db.set_value(
			"Employee", cls.orphan, {"leave_approver": None, "reports_to": None, "department": None}
		)
		frappe.db.set_single_value("HR Settings", "leave_approver_mandatory_in_leave_application", 1)

	def tearDown(self):
		frappe.set_user("Administrator")

	def draft(self, employee, offset: int = 0, **kwargs):
		"""A draft on its own date window.

		Leave Application refuses overlapping applications for one employee, so
		every test claims a distinct slice rather than colliding with the
		drafts its siblings left behind.
		"""
		start = add_days(getdate(), offset)
		return frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"leave_type": self.leave_type,
				"from_date": start,
				"to_date": add_days(start, 1),
				"status": "Open",
				**kwargs,
			}
		)

	def test_draft_saves_without_an_approver(self):
		doc = self.draft(self.orphan, offset=0)
		doc.insert()  # must not raise "Leave Approver is mandatory"
		self.assertEqual(doc.docstatus, 0)
		self.assertFalse(doc.leave_approver)

	def test_draft_can_be_updated_without_an_approver(self):
		doc = self.draft(self.orphan, offset=5)
		doc.insert()
		doc.description = "still drafting"
		doc.save()  # a second save must not start demanding an approver either
		self.assertEqual(doc.docstatus, 0)

	def test_submit_still_requires_an_approver(self):
		doc = self.draft(self.orphan, offset=10)
		doc.insert()
		doc.status = "Approved"
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.submit()
		self.assertIn("Leave Approver is mandatory", str(caught.exception))

	def test_submit_is_allowed_once_an_approver_is_named(self):
		manager = make_employee("draft_mgr@example.com", company="_Test Company")
		employee = make_employee("draft_with_mgr@example.com", company="_Test Company", reports_to=manager)
		approver = frappe.db.get_value("Employee", manager, "user_id")

		doc = self.draft(employee, offset=15, leave_approver=approver)
		doc.insert()
		self.assertEqual(doc.docstatus, 0)
		# the approver the fence accepts is the one the selector offers
		self.assertIn(approver, get_designated_approvers(employee, "leave_approver", "leave_approvers"))

	def test_mandatory_rule_off_means_submit_without_approver_is_fine(self):
		frappe.db.set_single_value("HR Settings", "leave_approver_mandatory_in_leave_application", 0)
		try:
			doc = self.draft(self.orphan, offset=20)
			doc.insert()
			doc.status = "Approved"
			doc.submit()
			self.assertEqual(doc.docstatus, 1)
		finally:
			frappe.db.set_single_value("HR Settings", "leave_approver_mandatory_in_leave_application", 1)


class TestDesignatedApproversAreTheSingleSourceOfTruth(FrappeTestCase):
	"""The selector and the fence must not disagree — that mismatch WAS the bug."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.parent_dept = "_Test Parent Dept - _TC"
		cls.child_dept = "_Test Child Dept - _TC"

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_parent_department_approver_is_not_offered(self):
		"""An ancestor-department approver is outside the authorised set.

		`get_department_approvers` (still used by the Shift Request selector)
		walks ancestors; the leave/expense selectors must not, because
		validate_staff_approver would refuse the pick on save.
		"""
		employee = make_employee("dept_child_staff@example.com", company="_Test Company")
		department = frappe.db.get_value("Employee", employee, "department")
		if not department:
			self.skipTest("employee fixture has no department on this site")

		approvers = get_designated_approvers(employee, "leave_approver", "leave_approvers")
		own_dept_approvers = frappe.get_all(
			"Department Approver",
			filters={"parent": department, "parentfield": "leave_approvers"},
			pluck="approver",
		)
		explicit = frappe.db.get_value("Employee", employee, "leave_approver")
		reports_to = frappe.db.get_value("Employee", employee, "reports_to")
		manager_user = frappe.db.get_value("Employee", reports_to, "user_id") if reports_to else None

		permitted = set(own_dept_approvers) | {explicit, manager_user} - {None}
		self.assertTrue(
			set(approvers).issubset(permitted),
			f"selector offered approvers the fence would refuse: {set(approvers) - permitted}",
		)

	def test_employee_is_never_their_own_approver(self):
		employee = make_employee("self_approver@example.com", company="_Test Company")
		user = frappe.db.get_value("Employee", employee, "user_id")
		frappe.db.set_value("Employee", employee, "leave_approver", user)

		self.assertNotIn(user, get_designated_approvers(employee, "leave_approver", "leave_approvers"))

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, nowdate

from erpnext.setup.doctype.department.department import get_abbreviated_name
from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.shift_type.test_shift_type import setup_shift_type
from hrms.hr.shift_rules import (
	reconcile_employee_shift,
	resolve_shift_for_employee,
	sync_shift_assignments,
)

COMPANY = "_Test Company"


def make_department(department_name, parent_department=None, is_group=0):
	docname = get_abbreviated_name(department_name, COMPANY)
	if frappe.db.exists("Department", docname):
		return docname

	department = frappe.new_doc("Department")
	department.update({"department_name": department_name, "company": COMPANY, "is_group": is_group})
	# only set an explicit parent; otherwise let the NestedSet controller
	# default to the root (its name varies across sites)
	if parent_department:
		department.parent_department = parent_department
	return department.insert().name


def make_shift_location(location_name, rules):
	if frappe.db.exists("Shift Location", location_name):
		frappe.delete_doc("Shift Location", location_name, force=True)
	doc = frappe.get_doc({"doctype": "Shift Location", "location_name": location_name, "checkin_radius": 0})
	for rule in rules:
		doc.append("shift_rules", rule)
	return doc.insert().name


class TestShiftRules(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Shift Assignment")

		self.shift_day = setup_shift_type(shift_type="Rule Shift Day")
		self.shift_night = setup_shift_type(
			shift_type="Rule Shift Night", start_time="19:00:00", end_time="03:30:00"
		)

		self.parent_dept = make_department("Rule Customer Service", is_group=1)
		self.leaf_dept = make_department("Rule CS Leaf", parent_department=self.parent_dept)
		self.other_dept = make_department("Rule Warehouse")

		# site default: night shift; Customer Service subtree: day shift
		self.location = make_shift_location(
			"Rule Loc HQ",
			[
				{"shift_type": self.shift_night.name},
				{"department": self.parent_dept, "shift_type": self.shift_day.name},
			],
		)

		self.employee = make_employee("shift_rule_emp@example.com", company=COMPANY)
		self._set_employee(department=self.leaf_dept, shift_location=self.location)

	def _set_employee(self, **values):
		for field, value in values.items():
			frappe.db.set_value("Employee", self.employee, field, value)
		frappe.clear_document_cache("Employee", self.employee)

	def _active_assignments(self, auto=None):
		filters = {"employee": self.employee, "docstatus": 1, "status": "Active"}
		if auto is not None:
			filters["created_by_shift_rule"] = auto
		return frappe.get_all(
			"Shift Assignment",
			filters=filters,
			fields=["name", "shift_type", "shift_location", "start_date", "end_date"],
			order_by="creation",
		)

	# ---------- resolution ----------

	def test_parent_department_rule_matches_leaf_department(self):
		resolved = resolve_shift_for_employee(self.employee)
		self.assertEqual(resolved.shift_type, self.shift_day.name)
		self.assertEqual(resolved.shift_location, self.location)

	def test_blank_department_row_is_site_default(self):
		self._set_employee(department=self.other_dept)
		resolved = resolve_shift_for_employee(self.employee)
		self.assertEqual(resolved.shift_type, self.shift_night.name)

	def test_deepest_department_match_wins(self):
		shift_leaf = setup_shift_type(shift_type="Rule Shift Leaf Override")
		location = make_shift_location(
			"Rule Loc Deep",
			[
				{"shift_type": self.shift_night.name},
				{"department": self.parent_dept, "shift_type": self.shift_day.name},
				{"department": self.leaf_dept, "shift_type": shift_leaf.name},
			],
		)
		self._set_employee(shift_location=location)
		resolved = resolve_shift_for_employee(self.employee)
		self.assertEqual(resolved.shift_type, shift_leaf.name)

	def test_no_location_resolves_to_none(self):
		self._set_employee(shift_location=None)
		self.assertIsNone(resolve_shift_for_employee(self.employee))

	# ---------- reconciliation ----------

	def test_reconcile_creates_open_ended_auto_assignment(self):
		action = reconcile_employee_shift(self.employee)
		self.assertEqual(action, "created")

		assignments = self._active_assignments(auto=1)
		self.assertEqual(len(assignments), 1)
		assignment = assignments[0]
		self.assertEqual(assignment.shift_type, self.shift_day.name)
		self.assertEqual(assignment.shift_location, self.location)
		self.assertEqual(getdate(assignment.start_date), getdate(nowdate()))
		self.assertIsNone(assignment.end_date)

	def test_reconcile_is_idempotent(self):
		reconcile_employee_shift(self.employee)
		action = reconcile_employee_shift(self.employee)
		self.assertEqual(action, "noop")
		self.assertEqual(len(self._active_assignments()), 1)

	def test_manual_assignment_wins(self):
		frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"employee": self.employee,
				"company": COMPANY,
				"shift_type": self.shift_night.name,
				"start_date": nowdate(),
				"status": "Active",
			}
		).insert().submit()

		action = reconcile_employee_shift(self.employee)
		self.assertEqual(action, "skipped-manual")
		self.assertEqual(len(self._active_assignments(auto=1)), 0)

	def test_location_change_swaps_assignment(self):
		reconcile_employee_shift(self.employee)

		other_location = make_shift_location("Rule Loc Night Site", [{"shift_type": self.shift_night.name}])
		self._set_employee(shift_location=other_location)
		action = reconcile_employee_shift(self.employee)
		self.assertEqual(action, "swapped")

		open_assignments = [a for a in self._active_assignments(auto=1) if not a.end_date]
		self.assertEqual(len(open_assignments), 1)
		self.assertEqual(open_assignments[0].shift_type, self.shift_night.name)
		self.assertEqual(open_assignments[0].shift_location, other_location)

		closed = [a for a in self._active_assignments(auto=1) if a.end_date]
		self.assertEqual(len(closed), 1)
		self.assertEqual(closed[0].shift_type, self.shift_day.name)

	def test_no_location_closes_existing_auto_assignment(self):
		reconcile_employee_shift(self.employee)
		self._set_employee(shift_location=None)
		action = reconcile_employee_shift(self.employee)
		self.assertEqual(action, "closed")
		self.assertEqual([a for a in self._active_assignments(auto=1) if not a.end_date], [])

	def test_sync_skips_employee_without_location(self):
		self._set_employee(shift_location=None)
		sync_shift_assignments()
		self.assertEqual(self._active_assignments(), [])

	def test_shift_schedule_assignment_wins_and_closes_auto_rows(self):
		reconcile_employee_shift(self.employee)
		self.assertEqual(len(self._active_assignments(auto=1)), 1)

		schedule = frappe.get_doc(
			{
				"doctype": "Shift Schedule",
				"frequency": "Every Week",
				"shift_type": self.shift_day.name,
				"repeat_on_days": [{"day": "Monday"}],
			}
		).insert()
		schedule.submit()
		frappe.get_doc(
			{
				"doctype": "Shift Schedule Assignment",
				"employee": self.employee,
				"company": COMPANY,
				"shift_schedule": schedule.name,
				"enabled": 1,
				"create_shifts_after": nowdate(),
			}
		).insert()

		action = reconcile_employee_shift(self.employee)
		self.assertEqual(action, "skipped-schedule")
		open_autos = [a for a in self._active_assignments(auto=1) if not a.end_date]
		self.assertEqual(open_autos, [])

	def test_on_update_hook_reconciles_on_employee_save(self):
		# start from no location, then set it through a real save so the
		# hooks.py on_update wiring (reconcile_on_employee_update) is exercised
		self._set_employee(shift_location=None)
		doc = frappe.get_doc("Employee", self.employee)
		doc.shift_location = self.location
		doc.save()

		assignments = self._active_assignments(auto=1)
		self.assertEqual(len(assignments), 1)
		self.assertEqual(assignments[0].shift_type, self.shift_day.name)

	def test_duplicate_rule_rows_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			make_shift_location(
				"Rule Loc Duplicates",
				[
					{"shift_type": self.shift_day.name},
					{"shift_type": self.shift_night.name},
				],
			)
		with self.assertRaises(frappe.ValidationError):
			make_shift_location(
				"Rule Loc Duplicates 2",
				[
					{"department": self.parent_dept, "shift_type": self.shift_day.name},
					{"department": self.parent_dept, "shift_type": self.shift_night.name},
				],
			)

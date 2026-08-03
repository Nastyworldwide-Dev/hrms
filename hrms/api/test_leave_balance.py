# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, flt, get_year_ending, getdate

from hrms.api import get_leave_balance_map
from hrms.hr.doctype.leave_period.test_leave_period import create_leave_period
from hrms.hr.doctype.leave_policy_assignment.test_service_band_assignment import (
	AL_SLABS,
	GRADE_D,
	make_band_employee,
	make_banded_leave_type,
	make_policy,
)
from hrms.hr.doctype.leave_type.test_leave_type import create_employee_grade

test_dependencies = ["Employee"]


def make_plain_leave_type(name, **kwargs):
	if frappe.db.exists("Leave Type", name):
		frappe.delete_doc("Leave Type", name, force=True)
	return (
		frappe.get_doc({"doctype": "Leave Type", "leave_type_name": name, "include_holiday": 1, **kwargs})
		.insert()
		.name
	)


def make_allocation(employee, leave_type, from_date, to_date, leaves, carry_forward=0):
	allocation = frappe.get_doc(
		{
			"doctype": "Leave Allocation",
			"employee": employee,
			"leave_type": leave_type,
			"from_date": from_date,
			"to_date": to_date,
			"new_leaves_allocated": leaves,
			"carry_forward": carry_forward,
		}
	).insert()
	allocation.submit()
	return allocation


class TestLeaveBalanceMap(FrappeTestCase):
	"""hrms.api.get_leave_balance_map must expose the ANNUAL entitlement as the
	gauge denominator: service-entitlement slab -> policy annual_allocation ->
	allocated (in that order), never 0/None for a displayed card."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_employee_grade(GRADE_D)

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

		# policy amount 99 is the unbanded fallback — a 99 entitlement would
		# prove the slab lookup did not happen (mirrors the service-band suite)
		self.annual = make_banded_leave_type("_Test Band Annual Leave", AL_SLABS)
		self.policy = make_policy("Test Band Policy", [(self.annual, 99)])

		self.period_start = getdate(f"{getdate().year}-01-01")
		self.period = create_leave_period(
			self.period_start, get_year_ending(self.period_start), "_Test Company"
		)

	def submit_period_assignment(self, employee, policy=None, carry_forward=0):
		assignment = frappe.get_doc(
			{
				"doctype": "Leave Policy Assignment",
				"employee": employee,
				"assignment_based_on": "Leave Period",
				"leave_policy": (policy or self.policy).name,
				"leave_period": self.period.name,
				"carry_forward": carry_forward,
			}
		).insert()
		assignment.submit()
		return assignment

	# --- annual entitlement resolution ---

	def test_prorated_mid_year_joiner_shows_full_entitlement(self):
		# DOJ inside the period -> allocation pro-rated below the 0-2y slab (14),
		# but the denominator must stay the full 14
		doj = add_days(self.period_start, 82)  # ~24 Mar
		employee = make_band_employee("balance_prorated@example.com", GRADE_D, doj)
		self.submit_period_assignment(employee)

		entry = get_leave_balance_map(employee)[self.annual]

		self.assertEqual(flt(entry["annual_entitlement"]), 14.0)
		self.assertLess(flt(entry["allocated_leaves"]), 14.0)
		self.assertEqual(flt(entry["balance_leaves"]), flt(entry["allocated_leaves"]))
		self.assertEqual(flt(entry["carry_forwarded_leaves"]), 0.0)

	def test_full_year_employee_allocated_equals_entitlement(self):
		# joined 3y before period start -> 2-5y slab (18), no pro-ration
		doj = add_months(self.period_start, -36)
		employee = make_band_employee("balance_full_year@example.com", GRADE_D, doj)
		self.submit_period_assignment(employee)

		entry = get_leave_balance_map(employee)[self.annual]

		self.assertEqual(flt(entry["annual_entitlement"]), 18.0)
		self.assertEqual(flt(entry["allocated_leaves"]), 18.0)

	def test_manual_allocation_falls_back_to_allocated(self):
		# Replacement/compensatory style: no policy, manual allocation only ->
		# denominator = allocated (current behavior), never 0
		leave_type = make_plain_leave_type("_Test Balance Replacement Leave")
		employee = make_band_employee(
			"balance_manual@example.com", GRADE_D, add_months(self.period_start, -24)
		)
		make_allocation(employee, leave_type, self.period_start, get_year_ending(self.period_start), 3)

		entry = get_leave_balance_map(employee)[leave_type]

		self.assertEqual(flt(entry["annual_entitlement"]), 3.0)
		self.assertEqual(flt(entry["allocated_leaves"]), 3.0)

	def test_no_grade_falls_back_to_policy_annual_allocation(self):
		# every AL slab is grade-specific -> lookup misses for a grade-less
		# employee -> policy annual_allocation (99) becomes the denominator
		doj = add_days(self.period_start, 82)
		employee = make_band_employee("balance_no_grade@example.com", None, doj)
		self.submit_period_assignment(employee)

		entry = get_leave_balance_map(employee)[self.annual]

		self.assertEqual(flt(entry["annual_entitlement"]), 99.0)
		self.assertLess(flt(entry["allocated_leaves"]), 99.0)

	def test_carry_forward_reported_but_not_in_denominator(self):
		# 18 unused leaves from last period + 18 new -> allocated 36, but the
		# denominator stays the 18-day entitlement and carried leaves surface
		cf_type = make_banded_leave_type("_Test Band CF Annual Leave", AL_SLABS, is_carry_forward=1)
		policy = make_policy("Test Band CF Policy", [(cf_type, 99)])
		doj = add_months(self.period_start, -36)
		employee = make_band_employee("balance_cf@example.com", GRADE_D, doj)
		make_allocation(
			employee,
			cf_type,
			add_months(self.period_start, -12),
			add_days(self.period_start, -1),
			18,
		)
		self.submit_period_assignment(employee, policy=policy, carry_forward=1)

		entry = get_leave_balance_map(employee)[cf_type]

		self.assertEqual(flt(entry["annual_entitlement"]), 18.0)
		self.assertEqual(flt(entry["allocated_leaves"]), 36.0)
		self.assertEqual(flt(entry["carry_forwarded_leaves"]), 18.0)
		self.assertEqual(flt(entry["balance_leaves"]), 36.0)

	def test_lwp_type_excluded_from_map(self):
		lwp_type = make_plain_leave_type("_Test Balance LWP", is_lwp=1)
		employee = make_band_employee("balance_lwp@example.com", GRADE_D, add_months(self.period_start, -24))
		make_allocation(employee, lwp_type, self.period_start, get_year_ending(self.period_start), 5)

		self.assertNotIn(lwp_type, get_leave_balance_map(employee))

	def test_unknown_employee_is_rejected(self):
		# permission guard doubles as a clean 404 for bad ids (no TypeError
		# from unpacking a missing Employee row)
		with self.assertRaises(frappe.DoesNotExistError):
			get_leave_balance_map("HR-EMP-DOES-NOT-EXIST")

	def test_every_entry_has_positive_denominator(self):
		# the card must never render n/0 regardless of how leave was granted
		leave_type = make_plain_leave_type("_Test Balance Odd Leave")
		employee = make_band_employee("balance_odd@example.com", GRADE_D, add_months(self.period_start, -24))
		make_allocation(employee, leave_type, self.period_start, get_year_ending(self.period_start), 0.5)

		for entry in get_leave_balance_map(employee).values():
			self.assertGreater(flt(entry["annual_entitlement"]), 0.0)


class TestGetLeaveTypes(FrappeTestCase):
	"""hrms.api.get_leave_types feeds the PWA leave application dropdown. It
	must keep working for a staff user whose role set lost Leave Type read
	(role drift): a permission-checked lookup here 403s the endpoint and the
	dropdown silently shows "No results found" while allocations exist."""

	def setUp(self):
		frappe.set_user("Administrator")
		for doctype in ["Leave Application", "Leave Allocation", "Leave Ledger Entry"]:
			frappe.db.delete(doctype)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_leave_types_resolve_without_leave_type_read_permission(self):
		from hrms.api import get_leave_types

		today = getdate()
		year_start = today.replace(month=1, day=1)
		leave_type = make_plain_leave_type("_Test Dropdown Leave")
		lwp_type = make_plain_leave_type("_Test Dropdown LWP", is_lwp=1)
		employee = make_band_employee("dropdown_staff@example.com", GRADE_D, add_months(year_start, -24))
		make_allocation(employee, leave_type, year_start, get_year_ending(year_start), 10)

		# simulate role drift: the employee's user keeps no roles at all
		user = frappe.db.get_value("Employee", employee, "user_id")
		user_doc = frappe.get_doc("User", user)
		original_roles = [r.role for r in user_doc.roles]
		user_doc.roles = []
		user_doc.save()
		self.addCleanup(self._restore_roles, user, original_roles)

		frappe.set_user(user)
		leave_types = get_leave_types(employee, str(today))

		self.assertIn(leave_type, leave_types)
		self.assertIn(lwp_type, leave_types)

	def test_other_employees_leave_details_stay_guarded(self):
		from hrms.hr.doctype.leave_application.leave_application import get_leave_details

		today = getdate()
		year_start = today.replace(month=1, day=1)
		employee = make_band_employee("dropdown_staff@example.com", GRADE_D, add_months(year_start, -24))
		other = make_band_employee("dropdown_other@example.com", GRADE_D, add_months(year_start, -24))

		frappe.set_user(frappe.db.get_value("Employee", employee, "user_id"))
		with self.assertRaises(frappe.PermissionError):
			get_leave_details(other, today)

	@staticmethod
	def _restore_roles(user, roles):
		frappe.set_user("Administrator")
		user_doc = frappe.get_doc("User", user)
		user_doc.roles = []
		for role in roles:
			user_doc.append("roles", {"role": role})
		user_doc.save()

	def test_balance_map_resolves_for_role_less_own_employee(self):
		# staff whose role set lost Employee read must still see their own
		# cards — the guard's own-employee check runs before has_permission
		today = getdate()
		year_start = today.replace(month=1, day=1)
		leave_type = make_plain_leave_type("_Test Dropdown Leave")
		employee = make_band_employee("dropdown_staff@example.com", GRADE_D, add_months(year_start, -24))
		make_allocation(employee, leave_type, year_start, get_year_ending(year_start), 10)

		user = frappe.db.get_value("Employee", employee, "user_id")
		user_doc = frappe.get_doc("User", user)
		original_roles = [r.role for r in user_doc.roles]
		user_doc.roles = []
		user_doc.save()
		self.addCleanup(self._restore_roles, user, original_roles)

		frappe.set_user(user)
		balance_map = get_leave_balance_map(employee)

		self.assertIn(leave_type, balance_map)

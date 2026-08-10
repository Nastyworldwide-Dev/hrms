import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_months, add_years, flt, get_year_ending, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.leave_period.test_leave_period import create_leave_period
from hrms.hr.doctype.leave_policy_assignment.leave_policy_assignment import (
	calculate_pro_rated_leaves,
)
from hrms.hr.doctype.leave_type.test_leave_type import create_employee_grade
from hrms.hr.service_band_audit import find_misbanded_allocations
from hrms.overrides.leave_policy_assignment_override import current_service_anniversary
from hrms.patches.v15_92_0.add_leave_type_do_not_prorate_field import (
	execute as add_do_not_prorate_field,
)

test_dependencies = ["Employee"]

GRADE_D = "_Test Band Grade D"
GRADE_F = "_Test Band Grade F"

# grade D: 0-2y -> 14, 2-5y -> 18, 5y+ -> 20; grade F: 0-5y -> 12, 5y+ -> 16
# (band rule: from_years <= completed_years < to_years, "To" exclusive)
AL_SLABS = [
	{"from_years": 0, "to_years": 2, "leave_days": 14, "grade": GRADE_D},
	{"from_years": 2, "to_years": 5, "leave_days": 18, "grade": GRADE_D},
	{"from_years": 5, "to_years": 99, "leave_days": 20, "grade": GRADE_D},
	{"from_years": 0, "to_years": 5, "leave_days": 12, "grade": GRADE_F},
	{"from_years": 5, "to_years": 99, "leave_days": 16, "grade": GRADE_F},
]


def make_banded_leave_type(name, slabs, **kwargs):
	if frappe.db.exists("Leave Type", name):
		frappe.delete_doc("Leave Type", name, force=True)
	doc = frappe.get_doc(
		{
			"doctype": "Leave Type",
			"leave_type_name": name,
			"based_on_years_of_service": 1,
			"include_holiday": 1,
			"service_entitlements": slabs,
			**kwargs,
		}
	)
	return doc.insert().name


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


def make_band_employee(email, grade, date_of_joining):
	name = make_employee(email, company="_Test Company")
	# make_employee returns an existing employee without applying kwargs,
	# so pin DOJ and grade explicitly to keep re-runs deterministic
	frappe.db.set_value("Employee", name, {"date_of_joining": getdate(date_of_joining), "grade": grade})
	return name


class TestServiceBandAssignment(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		add_do_not_prorate_field()
		create_employee_grade(GRADE_D)
		create_employee_grade(GRADE_F)

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

		self.annual = make_banded_leave_type("_Test Band Annual Leave", AL_SLABS)
		# policy amount 99 is the unbanded fallback — any 99 allocation would
		# prove the slab substitution did not happen
		self.policy = make_policy("Test Band Policy", [(self.annual, 99)])

	def submit_joining_assignment(self, employee, policy=None):
		assignment = frappe.get_doc(
			{
				"doctype": "Leave Policy Assignment",
				"employee": employee,
				"assignment_based_on": "Joining Date",
				"leave_policy": (policy or self.policy).name,
			}
		).insert()
		assignment.submit()
		return assignment

	def submit_period_assignment(self, employee, leave_period, policy=None):
		assignment = frappe.get_doc(
			{
				"doctype": "Leave Policy Assignment",
				"employee": employee,
				"assignment_based_on": "Leave Period",
				"leave_policy": (policy or self.policy).name,
				"leave_period": leave_period.name,
			}
		).insert()
		assignment.submit()
		return assignment

	def get_allocation(self, assignment, leave_type):
		return frappe.get_value(
			"Leave Allocation",
			{"leave_policy_assignment": assignment.name, "leave_type": leave_type, "docstatus": 1},
			["from_date", "to_date", "new_leaves_allocated"],
			as_dict=True,
		)

	def assert_anniversary_window(self, allocation, date_of_joining):
		doj = getdate(date_of_joining)
		today = getdate()
		expected_from = current_service_anniversary(doj)
		self.assertEqual(getdate(allocation.from_date), expected_from)
		self.assertEqual(getdate(allocation.to_date), add_days(add_months(expected_from, 12), -1))
		# structural checks that don't reuse the helper under test:
		# the window starts on a joining anniversary, covers today, spans one year
		self.assertEqual(
			(getdate(allocation.from_date).month, getdate(allocation.from_date).day),
			(doj.month, doj.day),
		)
		self.assertLessEqual(getdate(allocation.from_date), today)
		self.assertGreater(getdate(allocation.to_date), today)

	# --- BUG 1 + BUG 2: Joining Date basis ---

	def test_anniversary_helper_edge_dates(self):
		# Feb-29 DOJ clamps to Feb 28 in non-leap years...
		self.assertEqual(current_service_anniversary("2024-02-29", "2026-07-23"), getdate("2026-02-28"))
		# ...and lands back on Feb 29 in leap years
		self.assertEqual(current_service_anniversary("2024-02-29", "2028-03-01"), getdate("2028-02-29"))
		# a future DOJ clamps to zero completed years -> anniversary is the DOJ itself
		self.assertEqual(current_service_anniversary("2030-07-01", "2026-07-23"), getdate("2030-07-01"))

	def test_tenured_employee_gets_current_band_and_one_year_window(self):
		doj = add_months(getdate(), -55)  # ~4.6 years of service
		employee = make_band_employee("band_d_tenured@example.com", GRADE_D, doj)
		assignment = self.submit_joining_assignment(employee)
		allocation = self.get_allocation(assignment, self.annual)

		self.assertEqual(flt(allocation.new_leaves_allocated), 18.0)  # 2-5y band, NOT 14
		self.assert_anniversary_window(allocation, doj)
		# the window must never start at the historical DOJ
		self.assertNotEqual(getdate(allocation.from_date), getdate(doj))

	def test_new_joiner_keeps_first_band_and_doj_window(self):
		doj = add_days(getdate(), -5)  # joined this month
		employee = make_band_employee("band_d_new@example.com", GRADE_D, doj)
		assignment = self.submit_joining_assignment(employee)
		allocation = self.get_allocation(assignment, self.annual)

		self.assertEqual(flt(allocation.new_leaves_allocated), 14.0)  # 0-2y band
		# a new joiner's current anniversary IS the DOJ
		self.assertEqual(getdate(allocation.from_date), getdate(doj))
		self.assertEqual(getdate(allocation.to_date), add_days(add_months(getdate(doj), 12), -1))

	def test_senior_grade_five_plus_band(self):
		doj = add_months(getdate(), -72)  # 6 years of service
		employee = make_band_employee("band_f_senior@example.com", GRADE_F, doj)
		assignment = self.submit_joining_assignment(employee)
		allocation = self.get_allocation(assignment, self.annual)

		self.assertEqual(flt(allocation.new_leaves_allocated), 16.0)  # grade F 5y+ band
		self.assert_anniversary_window(allocation, doj)

	def test_band_boundaries_are_half_open(self):
		# documented rule: from_years <= completed_years < to_years ("To" exclusive)
		# exactly 2.0 years -> the 2-5 band
		employee = make_band_employee("band_d_exactly_two@example.com", GRADE_D, add_years(getdate(), -2))
		assignment = self.submit_joining_assignment(employee)
		allocation = self.get_allocation(assignment, self.annual)
		self.assertEqual(flt(allocation.new_leaves_allocated), 18.0)
		# on the anniversary day itself the window starts today
		self.assertEqual(getdate(allocation.from_date), getdate())

		# exactly 5.0 years -> the 5+ band
		employee = make_band_employee("band_d_exactly_five@example.com", GRADE_D, add_years(getdate(), -5))
		assignment = self.submit_joining_assignment(employee)
		allocation = self.get_allocation(assignment, self.annual)
		self.assertEqual(flt(allocation.new_leaves_allocated), 20.0)

	# --- Leave Period basis ---

	def test_leave_period_basis_uses_period_start_tenure_and_period_window(self):
		doj = add_months(getdate(), -55)
		employee = make_band_employee("band_d_period@example.com", GRADE_D, doj)
		period_start = getdate(f"{getdate().year}-01-01")
		leave_period = create_leave_period(period_start, get_year_ending(period_start), "_Test Company")
		assignment = self.submit_period_assignment(employee, leave_period)
		allocation = self.get_allocation(assignment, self.annual)

		# tenure evaluated at period start -> 2-5y band; DOJ before period start
		# -> full amount (no pro-ration regression)
		self.assertEqual(flt(allocation.new_leaves_allocated), 18.0)
		self.assertEqual(getdate(allocation.from_date), period_start)
		self.assertEqual(getdate(allocation.to_date), get_year_ending(period_start))

	def test_leave_period_mid_period_joiner_prorates_al_only(self):
		# fixed future window keeps this fully deterministic: period 2030,
		# joiner on 2030-07-01 -> 0-2 band for both types
		medical = make_banded_leave_type(
			"_Test Band Medical Leave",
			[
				{"from_years": 0, "to_years": 2, "leave_days": 14, "grade": GRADE_D},
				{"from_years": 2, "to_years": 99, "leave_days": 22, "grade": GRADE_D},
			],
			custom_do_not_prorate=1,
		)
		policy = make_policy("Test Band Period Policy", [(self.annual, 99), (medical, 99)])
		doj = getdate("2030-07-01")
		employee = make_band_employee("band_d_midperiod@example.com", GRADE_D, doj)
		leave_period = create_leave_period("2030-01-01", "2030-12-31", "_Test Company")
		assignment = self.submit_period_assignment(employee, leave_period, policy)

		# AL: banded to 14, then prorated for the July joiner (184/365 -> 7)
		al = self.get_allocation(assignment, self.annual)
		expected_al = calculate_pro_rated_leaves(14, doj, getdate("2030-01-01"), getdate("2030-12-31"))
		self.assertEqual(flt(al.new_leaves_allocated), flt(expected_al))
		self.assertEqual(flt(al.new_leaves_allocated), 7.0)

		# Medical: banded to 14 and flagged custom_do_not_prorate -> full band amount
		med = self.get_allocation(assignment, medical)
		self.assertEqual(flt(med.new_leaves_allocated), 14.0)

	# --- audit report ---

	def test_audit_flags_legacy_misbanded_allocation(self):
		doj = add_months(getdate(), -55)
		employee = make_band_employee("band_d_audit@example.com", GRADE_D, doj)
		assignment = self.submit_joining_assignment(employee)
		allocation_name = frappe.get_value(
			"Leave Allocation", {"leave_policy_assignment": assignment.name}, "name"
		)

		# a post-fix allocation is clean
		self.assertEqual(find_misbanded_allocations(), [])

		# simulate a pre-fix allocation: DOJ-anchored multi-year window, 0-2 band days
		frappe.db.set_value(
			"Leave Allocation",
			allocation_name,
			{
				"from_date": getdate(doj),
				"to_date": get_year_ending(getdate()),
				"new_leaves_allocated": 14,
			},
		)
		rows = find_misbanded_allocations()
		self.assertEqual(len(rows), 1)
		row = rows[0]
		self.assertEqual(row["employee"], employee)
		self.assertEqual(row["leave_allocation"], allocation_name)
		self.assertEqual(row["current_days"], 14.0)
		self.assertEqual(row["expected_days"], 18.0)
		self.assertIn("window is not the current anniversary year", row["reasons"])
		self.assertIn("allocated days do not match the service band", row["reasons"])

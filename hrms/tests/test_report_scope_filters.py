"""`apply_employee_scope` must hand back filters a query builder can consume.

The helper fences Script Reports, which run their own SQL and get no row scope
from the framework. It used to express the HR company fence as

    filters["company"] = ("in", companies)

which is `frappe.get_all` filter syntax. Both consumers feed the dict straight
to the query builder as an EQUALITY operand — `employee_advance_summary` as
`EmployeeAdvance.company == filters.get("company")`, and `shift_attendance`
through a loop over every key, `attendance[field] == filters[field]`. pypika
renders that as

    WHERE "company"=('in',['Company A'])

which is not valid SQL on MariaDB. It fires only for an HR caller who carries a
Company User Permission and leaves the company filter blank — exactly the
HR (Company) / HR (Instance) population the fence exists for. Unfenced HR gets
`allowed_companies() == []` and never reaches the branch, which is why nobody
hit it.

The contract is now: **`apply_employee_scope` returns scalar filter values
only.** The company fence is a separate list from `scoped_companies()`, so each
report writes its own `isin(...)`, and `shift_attendance`'s blind loop cannot be
handed something it will mis-render.

`hrms/tests/test_report_scope.py` pins the other half — that `is_hr` delegates
rather than restating the role rule.

Bench-free: `frappe` and the two hrms helpers are stubbed. Run it as a FILE:

    python3 hrms/tests/test_report_scope_filters.py
"""

import ast
import importlib.util
import pathlib
import sys
import types
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = HRMS_ROOT / "utils" / "report_scope.py"
REPORTS = HRMS_ROOT / "hr" / "report"


def load_module(*, is_hr, employee, companies):
	"""report_scope with its three collaborators stubbed."""
	frappe = types.ModuleType("frappe")
	frappe._dict = dict
	frappe.session = types.SimpleNamespace(user="someone@example.com")
	sys.modules["frappe"] = frappe

	hr_utils = types.ModuleType("hrms.hr.utils")
	hr_utils.sees_all_employee_data = lambda user=None: is_hr
	sys.modules["hrms.hr.utils"] = hr_utils

	identity = types.ModuleType("hrms.utils.identity")
	identity.get_employee = lambda: employee
	sys.modules["hrms.utils.identity"] = identity

	company_scope = types.ModuleType("hrms.overrides.company_scope")
	company_scope.allowed_companies = lambda user=None: list(companies)
	sys.modules["hrms.overrides.company_scope"] = company_scope

	spec = importlib.util.spec_from_file_location("report_scope_under_test", SOURCE)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def is_scalar(value):
	return not isinstance(value, (list, tuple, set, dict))


class TestFiltersStayScalar(unittest.TestCase):
	"""The defect, stated as a property: nothing a query builder receives as an
	equality operand may be a sequence."""

	def test_fenced_hr_gets_no_sequence_in_the_filters(self):
		module = load_module(is_hr=True, employee=None, companies=["Company A", "Company B"])
		filters = module.apply_employee_scope({"from_date": "2026-08-01"})
		self.assertTrue(
			all(is_scalar(v) for v in filters.values()),
			f"a sequence reached the query builder: {filters}",
		)

	def test_the_fence_is_still_available_separately(self):
		module = load_module(is_hr=True, employee=None, companies=["Company A", "Company B"])
		self.assertEqual(module.scoped_companies(), ["Company A", "Company B"])

	def test_unfenced_hr_is_unrestricted(self):
		module = load_module(is_hr=True, employee=None, companies=[])
		self.assertEqual(module.scoped_companies(), [])

	def test_hr_keeps_a_company_it_chose(self):
		module = load_module(is_hr=True, employee=None, companies=["Company A"])
		filters = module.apply_employee_scope({"company": "Company A"})
		self.assertEqual(filters["company"], "Company A")


class TestStaffScoping(unittest.TestCase):
	def test_staff_are_pinned_to_their_own_employee(self):
		module = load_module(is_hr=False, employee="HR-EMP-00001", companies=[])
		filters = module.apply_employee_scope({})
		self.assertEqual(filters["employee"], "HR-EMP-00001")

	def test_a_staff_request_for_someone_else_is_overridden(self):
		module = load_module(is_hr=False, employee="HR-EMP-00001", companies=[])
		filters = module.apply_employee_scope({"employee": "HR-EMP-00002"})
		self.assertEqual(filters["employee"], "HR-EMP-00001")

	def test_no_employee_record_returns_none_not_everything(self):
		"""None means the report renders zero rows. An unscoped filter set is
		exactly the hole this helper closes."""
		module = load_module(is_hr=False, employee=None, companies=[])
		self.assertIsNone(module.apply_employee_scope({}))

	def test_a_custom_employee_field_is_honoured(self):
		module = load_module(is_hr=False, employee="HR-EMP-00001", companies=[])
		filters = module.apply_employee_scope({}, employee_field="emp")
		self.assertEqual(filters["emp"], "HR-EMP-00001")


class TestConsumersUseTheList(unittest.TestCase):
	"""Static: every report that scopes itself must apply the fence with a
	set-membership predicate, never by dropping the list into `filters`."""

	CONSUMERS = ("shift_attendance", "employee_advance_summary")

	def test_each_consumer_calls_scoped_companies(self):
		for name in self.CONSUMERS:
			source = (REPORTS / name / f"{name}.py").read_text()
			self.assertIn("scoped_companies", source, name)

	def test_the_helper_never_builds_a_get_all_style_filter(self):
		"""`("in", …)` is `frappe.get_all` syntax, and both consumers treat every
		filter value as an operand.

		Read from the AST, not the text: the docstring quotes the old form to
		explain it, and a substring search cannot tell an example from a defect.
		"""
		tree = ast.parse(SOURCE.read_text())
		offenders = [
			ast.unparse(node)
			for node in ast.walk(tree)
			if isinstance(node, (ast.Tuple, ast.List))
			and node.elts
			and isinstance(node.elts[0], ast.Constant)
			and node.elts[0].value in ("in", "not in", "like", ">", "<", ">=", "<=")
		]
		self.assertEqual(offenders, [])


if __name__ == "__main__":
	unittest.main()

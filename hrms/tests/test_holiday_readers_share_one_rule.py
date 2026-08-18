"""Both holiday endpoints must serve a staff member's own calendar by one rule.

get_holidays_for_employee used to demand doctype-level Holiday List read on
top of the own-employee fence. On the hub that 403'd EVERY provisioned user:
identity provisioning grants the bare Employee role by design, while Holiday
List read ships only inside the ESS user-type bundle this hub does not use.
Meanwhile get_holidays_for_calendar served the SAME dates to the SAME user
with no such check — two readers, two rules, and the stricter one blocked
only legitimate traffic ("Could not load your holiday calendar" on the
Leaves dashboard, verifica-live 2026-08-18).

The rule both now follow, pinned here so a hardening pass cannot quietly
reintroduce the 403:

  * the own-employee fence IS the authorization — it must stay;
  * the holiday list is resolved SERVER-SIDE from that employee, never taken
    from the caller — so a doctype-level read check protects nothing;
  * neither reader calls has_permission.

Re-adding the check requires first deciding the ESS provisioning question —
see the comment at the call site. AST only, no bench.
"""

import ast
import pathlib
import unittest

API = pathlib.Path(__file__).resolve().parent.parent / "api" / "__init__.py"

READERS = ("get_holidays_for_employee", "get_holidays_for_calendar")


def _function(name: str):
	for node in ast.walk(ast.parse(API.read_text())):
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
			return node
	raise AssertionError(f"{name} not found in hrms/api/__init__.py")


def _calls(func) -> set:
	return {
		getattr(n.func, "id", None) or getattr(n.func, "attr", None)
		for n in ast.walk(func)
		if isinstance(n, ast.Call)
	}


class TestHolidayReadersShareOneRule(unittest.TestCase):
	def test_the_fence_stays(self):
		self.assertIn(
			"_ensure_own_employee_or_permitted",
			_calls(_function("get_holidays_for_employee")),
			"the own-employee fence is the authorization for this endpoint — it must not go",
		)
		# the calendar reader is fenced by its caller
		self.assertIn(
			"_ensure_own_employee_or_permitted",
			_calls(_function("get_attendance_calendar_events")),
			"the calendar entry point lost its fence",
		)

	def test_neither_reader_demands_doctype_read(self):
		for name in READERS:
			with self.subTest(reader=name):
				self.assertNotIn(
					"has_permission",
					_calls(_function(name)),
					f"{name} re-grew a doctype-level permission check — this is the "
					f"exact shape that 403'd every hub-provisioned user's own holiday "
					f"calendar. Read the rationale at the call site before hardening.",
				)

	def test_the_list_is_resolved_server_side(self):
		for name in READERS:
			with self.subTest(reader=name):
				self.assertIn(
					"get_holiday_list_for_employee",
					_calls(_function(name)),
					f"{name} no longer derives the holiday list from the fenced "
					f"employee — a caller-supplied list name would genuinely need "
					f"a permission check",
				)


if __name__ == "__main__":
	unittest.main()

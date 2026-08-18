"""Two session-shaped rules on the check-in flow, pinned at the source level.

  * TEAM CLOCK (D5): get_team_status decided "Not In Yet" vs "Absent" on the
    SITE clock. On a Dubai site a Malaysian member's shift end read four hours
    late — the exact skew hrms.utils.timezone exists to remove. The status
    derivation must take its now/today from employee_now(member), and the
    module must not import the system-clock helper at all.

  * INHERITANCE (D9): an OUT inherits remote approval from the IN of ITS OWN
    session. The old lookup was a same-calendar-day window, which both denied
    overnight shifts (yesterday's approved IN invisible next morning) and
    over-granted across sessions (an approved morning IN blessed an evening
    OUT past an unapproved second IN).

AST only — no bench required.
"""

import ast
import pathlib
import unittest

HRMS = pathlib.Path(__file__).resolve().parent.parent


def _source(rel: str) -> str:
	return (HRMS / rel).read_text()


def _function(rel: str, name: str):
	for node in ast.walk(ast.parse(_source(rel))):
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
			return node
	raise AssertionError(f"{name} not found in {rel}")


class TestTeamStatusUsesMemberClock(unittest.TestCase):
	def test_team_module_never_imports_the_system_clock(self):
		tree = ast.parse(_source("api/team.py"))
		imported = {
			alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) for alias in node.names
		}
		self.assertNotIn(
			"now_datetime",
			imported,
			"api/team.py imports now_datetime again — member status must run on "
			"employee_now(member), the member's own wall clock.",
		)
		self.assertIn("employee_now", imported)

	def test_status_derivation_is_fed_from_employee_now(self):
		func = _function("api/team.py", "get_team_status")
		calls = {
			getattr(node.func, "id", None) or getattr(node.func, "attr", None)
			for node in ast.walk(func)
			if isinstance(node, ast.Call)
		}
		self.assertIn("employee_now", calls)
		self.assertIn("derive_member_status", calls)


class TestOutInheritsFromItsOwnSession(unittest.TestCase):
	def test_lookup_is_keyed_to_the_latest_in_checkin(self):
		func = _function(
			"overrides/employee_checkin_after_insert.py", "_find_approved_in_request_for_session"
		)
		constants = {
			node.value
			for node in ast.walk(func)
			if isinstance(node, ast.Constant) and isinstance(node.value, str)
		}
		# keyed by the checkin link — the session — not by a day window
		self.assertIn("checkin", constants)
		self.assertNotIn(
			"00:00:00",
			" ".join(constants),
			"the calendar-day window is back — overnight OUTs will demand a second "
			"approval and cross-session OUTs will inherit one they should not",
		)

	def test_the_day_window_helper_is_gone(self):
		self.assertNotIn(
			"_find_approved_in_request_today",
			_source("overrides/employee_checkin_after_insert.py"),
			"both lookups exist — two definitions of 'which IN blesses this OUT' "
			"is the drift class this whole effort exists to end",
		)


if __name__ == "__main__":
	unittest.main()

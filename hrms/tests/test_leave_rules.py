"""Guards the single-writer boundary for hub scheduler jobs.

The cross-instance mirror is single-writer: a mirrored row (or a mirrored
employee's lifecycle) is owned by its source instance, and hub-side
db_set/db.set_value/qb.update writes bypass the doc-event guard in
hrms/sync/write_block.py. checkin_sweeper and hr/offboarding already
exclude mirrored rows at their queries; this guard pins that every hub
scheduler/API that writes a stamped doctype (or acts per-employee to
create one) carries the same `synced_from_instance is not set` exclusion,
so a new one added later without it fails here instead of double-counting
production balances at cutover.

Bench-free: reads the source of each site and asserts the exclusion sits
inside the function. Run it as a FILE:

    python3 hrms/tests/test_leave_rules.py
"""

import ast
import pathlib
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]

# (module path, function name, marker text that must appear in the function body)
SITES = [
	("hr/leave_rules.py", "auto_assign_leave_policies", "synced_from_instance"),
	("hr/utils.py", "get_leave_allocations", "synced_from_instance"),
	("hr/doctype/shift_type/shift_type.py", "get_employee_checkins", "synced_from_instance"),
	(
		"hr/doctype/shift_schedule_assignment/shift_schedule_assignment.py",
		"process_auto_shift_creation",
		"synced_from_instance",
	),
	(
		"hr/doctype/shift_assignment/shift_assignment.py",
		"mark_expired_shift_assignments_as_inactive",
		"synced_from_instance",
	),
	(
		"hr/doctype/attendance_allowance_type/attendance_allowance_type.py",
		"process_attendance_allowances",
		"synced_from_instance",
	),
]


def _function_source(module_path: str, func_name: str) -> str:
	source = (HRMS_ROOT / module_path).read_text()
	tree = ast.parse(source)
	for node in ast.walk(tree):
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == func_name:
			return ast.get_source_segment(source, node)
	raise AssertionError(f"{func_name} not found in {module_path}")


class TestMirrorExclusionAtEveryHubWriter(unittest.TestCase):
	def test_every_site_excludes_mirrored_rows(self):
		for module_path, func_name, marker in SITES:
			body = _function_source(module_path, func_name)
			self.assertIn(
				marker,
				body,
				f"{module_path}::{func_name} must exclude mirrored rows "
				f"({marker}) — hub schedulers are single-writer, see "
				f"hrms/sync/write_block.py",
			)

	def test_the_exclusion_is_the_not_set_form(self):
		# Guard against a stray "synced_from_instance" appearing in an
		# unrelated field list rather than as an exclusion filter.
		for module_path, func_name, _marker in SITES:
			body = _function_source(module_path, func_name)
			self.assertTrue(
				'"synced_from_instance": ("is", "not set")' in body
				or '"synced_from_instance": ["is", "not set"]' in body
				or "synced_from_instance.isnull()" in body,
				f"{module_path}::{func_name} names synced_from_instance but not as "
				f"an is-not-set / isnull exclusion",
			)


if __name__ == "__main__":
	unittest.main(verbosity=2)

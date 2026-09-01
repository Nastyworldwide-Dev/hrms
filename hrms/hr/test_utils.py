"""Guards the mirror exclusion on earned-leave accrual (get_leave_allocations).

Accrual writes the Leave Ledger hook-free (db_set + create_leave_ledger_entry),
so a mirrored allocation must be excluded at the query or its balance
double-counts against the source instance's own accrual. Bench-free source
guard; run as a FILE:

    python3 hrms/hr/test_utils.py
"""

import ast
import pathlib
import unittest

UTILS = pathlib.Path(__file__).resolve().parent / "utils.py"


def _function_source(func_name: str) -> str:
	source = UTILS.read_text()
	tree = ast.parse(source)
	for node in ast.walk(tree):
		if isinstance(node, ast.FunctionDef) and node.name == func_name:
			return ast.get_source_segment(source, node)
	raise AssertionError(f"{func_name} not found in {UTILS}")


class TestEarnedLeaveAccrualExcludesMirrored(unittest.TestCase):
	def test_get_leave_allocations_filters_mirrored(self):
		body = _function_source("get_leave_allocations")
		self.assertIn(
			"synced_from_instance.isnull()",
			body,
			"earned-leave accrual must skip mirrored allocations (single-writer, hrms/sync/write_block.py)",
		)


if __name__ == "__main__":
	unittest.main(verbosity=2)

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


def _pure_function(func_name: str):
	"""Exec a self-contained (frappe-free) function out of utils.py so its real
	behavior is testable without a bench."""
	namespace: dict = {}
	exec(_function_source(func_name), namespace)  # trusted local source, not user input
	return namespace[func_name]


class TestEarnedLeaveAccrualExcludesMirrored(unittest.TestCase):
	def test_get_leave_allocations_filters_mirrored(self):
		body = _function_source("get_leave_allocations")
		self.assertIn(
			"synced_from_instance.isnull()",
			body,
			"earned-leave accrual must skip mirrored allocations (single-writer, hrms/sync/write_block.py)",
		)


class TestReversibleDays(unittest.TestCase):
	"""_reversible_days clamps an RL reversal to what has NOT been taken — so a
	cancelled OT/claim can't push a Leave Allocation below leave already spent
	(LessAllocationError) and freeze the cancel."""

	def setUp(self):
		self.reversible = _pure_function("_reversible_days")

	def test_unconsumed_grant_fully_reverses(self):
		self.assertEqual(self.reversible(1.0, 0.0, 1.0), 1.0)

	def test_fully_consumed_grant_reverses_nothing(self):
		# 1 day granted, 1 day taken -> claw back nothing, cancel still proceeds
		self.assertEqual(self.reversible(1.0, 1.0, 1.0), 0.0)

	def test_partial_consumption_clamps_to_remainder(self):
		# allocation holds 2 days total, 1 taken -> only 1 is reversible
		self.assertEqual(self.reversible(2.0, 1.0, 1.0), 1.0)

	def test_never_goes_negative(self):
		# taken exceeds the whole allocation somehow -> reverse 0, never below
		self.assertEqual(self.reversible(1.0, 3.0, 1.0), 0.0)

	def test_half_day_grant(self):
		self.assertEqual(self.reversible(1.5, 1.0, 0.5), 0.5)

	def test_none_inputs_are_zero_safe(self):
		self.assertEqual(self.reversible(None, None, None), 0.0)


class TestReverseDoesNotValidate(unittest.TestCase):
	"""reverse_replacement_leave must NOT call allocation.validate(): validate()'s
	set_total_leaves_allocated throws 'Total leaves allocated is mandatory' when a
	sole grant is reversed to zero (Replacement Leave is neither earned nor
	compensatory), which would freeze the cancel. A reversal only reduces, so it
	decrements straight through db_set instead."""

	def test_reverse_avoids_validate(self):
		body = _function_source("reverse_replacement_leave")
		self.assertNotIn(
			".validate()",
			body,
			"reverse must not validate() — it freezes the cancel when a grant reverses to zero",
		)


if __name__ == "__main__":
	unittest.main(verbosity=2)

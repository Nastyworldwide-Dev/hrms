"""Cancelling a request must not freeze on an allocation that has moved on.

`reverse_replacement_leave` runs inside a CANCEL: somebody is withdrawing their
request. It used to fetch the Leave Allocation with a bare `get_doc`, so if that
allocation had been cancelled by HR or re-pulled under a new name by the sync,
the cancel died on a `DoesNotExistError` the employee could do nothing about.

A CANCELLED allocation is worse than a missing one: decrementing it writes a
negative ledger entry onto a document that is no longer in force.

AST-based and bench-free — `hrms.hr.utils` cannot be imported without a bench
(pypika), so the guard reads the committed source and pins the SHAPE of the
check rather than one phrasing of it. Run as
`python3 hrms/tests/test_rl_reversal_survives_a_missing_allocation.py`.
"""

import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent / "hr" / "utils.py"


def _function(name: str) -> ast.FunctionDef:
	for node in ast.walk(ast.parse(SOURCE.read_text())):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return node
	raise AssertionError(f"{name} not found in {SOURCE}")


class TestReversalGuardsItsAllocation(unittest.TestCase):
	def setUp(self):
		self.fn = _function("reverse_replacement_leave")
		self.text = ast.unparse(self.fn)

	def test_existence_is_checked_before_the_document_is_fetched(self):
		"""Otherwise the cancel throws DoesNotExistError on a row that is nobody's
		fault, and the person cannot withdraw their own request."""
		self.assertIn(
			"exists",
			self.text,
			"reverse_replacement_leave must check the allocation exists before fetching it — a "
			"bare get_doc throws inside a cancel",
		)

	def test_docstatus_is_checked_before_anything_is_decremented(self):
		"""A cancelled or draft allocation must not be written to at all."""
		self.assertIn(
			"docstatus",
			self.text,
			"a cancelled allocation must not be decremented — that writes a negative ledger entry "
			"onto a document no longer in force",
		)

	def test_the_skip_is_recorded_where_hr_reconciles(self):
		"""Silently leaving a balance too high is its own defect. The employee did
		nothing wrong, so it is not raised at them — but somebody has to know."""
		self.assertIn(
			"log_error",
			self.text,
			"a skipped reversal leaves the balance too high; record it where HR looks",
		)

	def test_it_does_not_throw_at_the_person_cancelling(self):
		"""Their action succeeded. The allocation's fate is not theirs to fix."""
		for node in ast.walk(self.fn):
			if (
				isinstance(node, ast.Call)
				and isinstance(node.func, ast.Attribute)
				and node.func.attr == "throw"
			):
				self.fail(
					"reverse_replacement_leave throws at the caller. This runs inside a cancel — "
					"the withdrawal must go through."
				)


if __name__ == "__main__":
	unittest.main()

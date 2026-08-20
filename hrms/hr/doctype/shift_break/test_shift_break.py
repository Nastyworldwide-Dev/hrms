"""Guard: Shift Break rows can never be configured-but-silently-inert.

The senior's v15.112.1 shipped the same three rejections on the live branch
(parent-level there); ours live on the CHILD controller, which Frappe runs on
every parent save. This pins the parity so neither branch's review can claim
the other lost it:

  * Flexible with a zero/blank duration -> rejected
  * Fixed missing either window bound   -> rejected
  * Fixed with an inverted window       -> rejected, and the message carries
    the midnight-crossing guidance (two rows: ...23:59:59 / 00:00:00...)
    adopted from v15.112.1 — night shifts are real on this group.

Deliberately NOT ported from v15.112.1, recorded here so nobody "fixes" it
in: mirroring the window length into break_hours plus its backfill patch.
Our Break Duration column is a VIRTUAL field computed from the same inputs
the deduction engine reads — a stored copy would go stale under the write
paths that skip validate (the shadow sync inserts with ignore_validate),
which is the drift disease this fork keeps curing.

AST/text-based and bench-free: run as
`python3 hrms/hr/doctype/shift_break/test_shift_break.py`.
"""

import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "shift_break.py"


class TestValidateRejectsInertRows(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.text = SOURCE.read_text()
		tree = ast.parse(cls.text)
		cls.validate = next(
			node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "validate"
		)
		cls.throws = [
			node
			for node in ast.walk(cls.validate)
			if isinstance(node, ast.Call)
			and isinstance(node.func, ast.Attribute)
			and node.func.attr == "throw"
		]

	def test_all_three_inert_shapes_are_rejected(self):
		self.assertGreaterEqual(
			len(self.throws),
			3,
			"validate must reject: Flexible without duration, Fixed missing a "
			"bound, Fixed with an inverted window",
		)

	def test_flexible_without_duration_is_rejected(self):
		self.assertIn("Flexible Shift Break requires a Break Duration", self.text)

	def test_fixed_missing_bounds_is_rejected(self):
		self.assertIn("requires both Start Time and End Time", self.text)

	def test_inverted_window_message_carries_the_midnight_guidance(self):
		self.assertIn(
			"crossing midnight",
			self.text,
			"the inverted-window rejection must explain the two-row encoding "
			"(23:59:59 / 00:00:00) — adopted from v15.112.1",
		)

	def test_no_stored_copy_of_the_window_length(self):
		self.assertNotIn(
			"self.break_hours =",
			self.text,
			"break_hours must never be machine-written here — the Break "
			"Duration column is virtual so display and engine cannot drift",
		)


if __name__ == "__main__":
	unittest.main()

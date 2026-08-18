"""A failed row in a sync pass must roll back itself, not the whole pass.

`sync_instance` commits once per doctype, so everything `sync_doctype` writes
is uncommitted until the pass ends. The per-row handler called a bare
`frappe.db.rollback()`, which therefore discarded EVERY row written since the
last commit — a failure at row 4,000 of a 5,000-row pull threw away the 3,999
rows already written, while `written`/`inserted` kept counting them.

Two consequences, both quiet:

  * the `HRMS Sync Run` record reported thousands of rows it had just discarded;
  * only the rows after the LAST error in a pass actually survived, so the
    mirror ended up non-contiguous while reporting success.

`hrms.sync.parity` then showed a variance the run record could not explain —
and a cutover gate that can never reach zero is one everybody learns to ignore,
which is the failure `parity.compare_doctype` is written to prevent.

`hrms.hr.leave_rules` and `hrms.hr.shift_rules` already had the right shape (a
savepoint per record); the sync runner was the outlier. This pins it.

AST only — no bench required.
"""

import ast
import pathlib
import unittest

RUNNER = pathlib.Path(__file__).resolve().parent.parent / "sync" / "runner.py"


def _function(name: str):
	tree = ast.parse(RUNNER.read_text())
	for node in ast.walk(tree):
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == name:
			return node
	raise AssertionError(f"{name} not found in hrms/sync/runner.py")


def _calls(func, attr: str) -> list[ast.Call]:
	return [
		node
		for node in ast.walk(func)
		if isinstance(node, ast.Call) and getattr(node.func, "attr", None) == attr
	]


class TestSyncRowIsolation(unittest.TestCase):
	def test_row_write_is_wrapped_in_a_savepoint(self):
		self.assertTrue(
			_calls(_function("sync_doctype"), "savepoint"),
			"sync_doctype must open a savepoint per row, or a single bad row discards "
			"every row written since the last per-doctype commit.",
		)

	def test_every_rollback_in_the_row_loop_names_a_savepoint(self):
		offenders = [
			call.lineno
			for call in _calls(_function("sync_doctype"), "rollback")
			if not any(kw.arg == "save_point" for kw in call.keywords)
		]
		self.assertEqual(
			offenders,
			[],
			"A bare frappe.db.rollback() inside sync_doctype undoes the whole "
			"uncommitted pass, not the failed row. Pass save_point=ROW_SAVEPOINT. "
			f"Offending line(s): {offenders}",
		)

	def test_doctype_level_rollback_stays_whole(self):
		"""The pass-level handler in `sync_instance` is a different case.

		There the whole doctype has failed, and discarding its uncommitted work is
		correct — earlier doctypes are already committed. It must NOT be converted
		to a savepoint rollback along with the row-level one.
		"""
		self.assertTrue(
			any(
				not any(kw.arg == "save_point" for kw in call.keywords)
				for call in _calls(_function("sync_instance"), "rollback")
			),
			"sync_instance's per-doctype handler should still roll the pass back whole.",
		)


if __name__ == "__main__":
	unittest.main()

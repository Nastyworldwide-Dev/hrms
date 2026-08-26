"""Two sources claiming the same row is a registration error, not data.

The mirror keys every row on the SOURCE's document name. That is correct while
each source owns distinct records, and it silently breaks the moment two
registered instances hold the same name — which is exactly what a dev instance
cloned from live is: the same employees, the same names, a second time.

Measured on a real database before this guard existed:

    after a pull from Nasty-Live   -> stamp is 'Nasty-Live'
    after a pull from Nasty-Dev    -> stamp is 'Nasty-Dev'
    rows in the hub for this employee: 1
    counted as Nasty-Live: 0
    counted as Nasty-Dev : 1

One row, and the provenance stamp flips to whoever synced last. Three things
break at once, and all three were observed in production before the cause was
known:

  * `purge_instance("Nasty-Dev")` deletes rows that came from LIVE, because the
    stamp is the only thing it can go on. A real record was lost this way;
  * parity for Nasty-Live counts stamped rows, so a dev sync makes live's count
    DROP and reports missing rows that are sitting right there;
  * the row's CONTENT is overwritten too, so live data quietly reverts to
    whatever the clone happened to hold.

So the first writer keeps the row and the second is refused. Not merged, not
last-write-wins: a document name is an identity claim, and when two sources make
the same claim the mirror cannot know which is right. Picking silently is how
all three failures above happened. Refusing is recoverable — a human unregisters
the instance that should not have been there, and nothing was lost meanwhile.

Bench-free: the decision is pure. Run it as a FILE:

    python3 hrms/sync/test_contested_rows.py
"""

import ast
import pathlib
import unittest

SOURCE = pathlib.Path(__file__).resolve().parent / "runner.py"


def _pure_decision():
	"""`plan_cross_instance_write`, lifted out of runner.py without a bench.

	The function is pure and the module is not — runner.py imports frappe at the
	top. Compiling just this definition keeps the test bench-free without the
	function having to live somewhere less obvious than beside its caller.
	"""
	tree = ast.parse(SOURCE.read_text())
	fn = next(
		(
			node
			for node in tree.body
			if isinstance(node, ast.FunctionDef) and node.name == "plan_cross_instance_write"
		),
		None,
	)
	assert fn is not None, "runner.plan_cross_instance_write is missing"
	namespace = {}
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SOURCE), "exec"), namespace)
	return namespace["plan_cross_instance_write"]


class TestTheDecision(unittest.TestCase):
	def setUp(self):
		self.plan = _pure_decision()

	def test_a_new_row_is_written(self):
		allowed, _ = self.plan(existing_stamp=None, instance_name="Nasty-Live")
		self.assertTrue(allowed)

	def test_an_instance_may_update_its_own_row(self):
		"""The ordinary case — every incremental pull re-writes rows it owns."""
		allowed, _ = self.plan(existing_stamp="Nasty-Live", instance_name="Nasty-Live")
		self.assertTrue(allowed)

	def test_a_second_instance_is_refused(self):
		allowed, reason = self.plan(existing_stamp="Nasty-Live", instance_name="Nasty-Dev")
		self.assertFalse(allowed)
		self.assertIn("Nasty-Live", reason)
		self.assertIn("Nasty-Dev", reason)

	def test_a_hub_owned_row_is_not_claimed_by_a_source(self):
		"""An unstamped row was written HERE. A source overwriting it would take
		a record that no source has, which is the same silent loss in reverse.

		Empty string as well as None: `_narrow_to_local_schema` can hand back a
		blank for a column that exists but was never populated, and a blank stamp
		is not a claim."""
		for blank in (None, ""):
			allowed, _ = self.plan(existing_stamp=blank, instance_name="Nasty-Dev")
			self.assertTrue(allowed, f"a {blank!r} stamp should not block the first writer")


class TestItIsWired(unittest.TestCase):
	"""The decision is worthless if the write path does not consult it.

	Read from the AST, not by grepping the file for the call — the module
	docstring above NAMES the function, and a text search would match that and
	pass on a runner that never calls it. This project has shipped that exact
	false pass twice (`test_report_scope_filters`, `test_health`).
	"""

	def setUp(self):
		self.tree = ast.parse(SOURCE.read_text())

	def _calls_within(self, func_name):
		fn = next(
			(
				n
				for n in ast.walk(self.tree)
				if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.name == func_name
			),
			None,
		)
		self.assertIsNotNone(fn, f"{func_name} is missing from runner.py")
		return {n.func.id for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}

	def test_the_row_writer_consults_it(self):
		self.assertIn("plan_cross_instance_write", self._calls_within("_write_row"))

	def test_the_refusal_is_a_distinct_outcome(self):
		"""Folding it into "skipped" would hide it. A create-only master that
		already exists is skipped and is FINE; a contested row is a registration
		error somebody has to act on, and a run that reports them as the same
		thing tells the operator nothing."""
		writer = next(
			n for n in ast.walk(self.tree) if isinstance(n, ast.FunctionDef) and n.name == "_write_row"
		)
		returned = {
			n.value.value
			for n in ast.walk(writer)
			if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)
		}
		self.assertIn("contested", returned)
		self.assertIn("skipped", returned, "the create-only outcome must still exist")


class TestARunThatWroteNothingFails(unittest.TestCase):
	"""A doctype that contested every row must RAISE, not report success.

	This is the sharpest form of the bug the guard introduces. A dev instance
	pulling into a hub that already holds live's rows contests every single one,
	so `errored` and `orphaned` are both 0 — and the old condition only looked at
	those two. The doctype would write nothing, report Completed, and
	`sync.health` counts a Completed run as proof the mirror is moving. The run
	proving the two instances collide would have looked like the healthiest one.
	"""

	def test_contested_is_in_the_no_rows_written_condition(self):
		tree = ast.parse(SOURCE.read_text())
		fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "sync_doctype")
		guard = next(
			(
				n
				for n in ast.walk(fn)
				if isinstance(n, ast.If)
				and any(isinstance(c, ast.Name) and c.id == "written" for c in ast.walk(n.test))
				and any(isinstance(c, ast.Name) and c.id == "pulled" for c in ast.walk(n.test))
			),
			None,
		)
		self.assertIsNotNone(guard, "the no-rows-written guard is missing from sync_doctype")
		names = {c.id for c in ast.walk(guard.test) if isinstance(c, ast.Name)}
		self.assertIn(
			"contested",
			names,
			"a doctype that contested every row writes nothing and would report success",
		)


if __name__ == "__main__":
	unittest.main()

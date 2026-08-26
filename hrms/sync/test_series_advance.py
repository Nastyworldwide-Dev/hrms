"""Mirroring a numbered row must move the counter, or nobody can create one.

REPRODUCED ON A REAL DATABASE, and it is the error HR hit in production:

    mirrored 3 rows (EMP-CKIN-08-2026-000001-000003). counter = 0
    EMPLOYEE CHECK-IN FAILED -> DuplicateEntryError:
        'EMP-CKIN-08-2026-000001' for key 'PRIMARY'

Employee Checkin autonames from a counter — `EMP-CKIN-.MM.-.YYYY.-.######` —
and `runner._write_row` inserts with `set_name=remote_name` so the mirror keeps
the SOURCE's document names. That is correct and load-bearing: the whole mirror
upserts on the remote name, and letting the hub renumber rows would duplicate
every one of them on the next pull.

But `set_name` bypasses `autoname` entirely, so `tabSeries` never advances. The
hub ends up holding EMP-CKIN-08-2026-000001..N while its counter still reads 0.
The next person to tap Check In is handed 000001, which is taken.

This is not a check-in bug. EVERY mirrored doctype that numbers itself has it —
Attendance (HR-ATT-.YYYY.-), Leave Application (HR-LAP-.YYYY.-), and the rest.
Check-in is simply the one an employee touches hourly, so it surfaced first.

The fix is to advance the counter past the highest number the mirror wrote, per
prefix. Deliberately only ever FORWARD: a hub that has already issued 000500
locally must not be wound back to 000003 because an older mirrored row arrived
late, or the collision reappears pointing the other way.

Bench-free: the parsing and the max are pure. Run it as a FILE:

    python3 hrms/sync/test_series_advance.py
"""

import ast
import pathlib
import unittest

SOURCE = pathlib.Path(__file__).resolve().parent / "runner.py"


WANTED = ("_SERIES_TOKENS", "series_regex", "split_series_name")


def _lift():
	"""The pure half of runner.py's series handling, without a bench.

	`series_matchers` is deliberately NOT lifted: it reads doctype meta, so it
	needs a site. Everything it feeds is pure and is tested here; the meta read
	itself is exercised on a real bench.
	"""
	body = ast.parse(SOURCE.read_text()).body
	wanted = [
		n
		for n in body
		if (isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef) and n.name in WANTED)
		or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in WANTED for t in n.targets))
	]
	assert len(wanted) == len(WANTED), f"lifted {len(wanted)} of {len(WANTED)}: {WANTED}"
	ns = {"re": __import__("re")}
	exec(compile(ast.Module(body=wanted, type_ignores=[]), str(SOURCE), "exec"), ns)
	return ns


def _split():
	"""split_series_name bound to Employee Checkin's declared pattern."""
	ns = _lift()
	matchers = [
		ns["series_regex"]("EMP-CKIN-.MM.-.YYYY.-.######"),
		ns["series_regex"]("HR-ATT-.YYYY.-"),
		ns["series_regex"]("HR-LAP-.YYYY.-"),
	]
	return lambda name: ns["split_series_name"](name, matchers)


class TestSplittingANumberedName(unittest.TestCase):
	def setUp(self):
		self.split = _split()

	def test_the_shape_that_broke_check_in(self):
		self.assertEqual(self.split("EMP-CKIN-08-2026-000001"), ("EMP-CKIN-08-2026-", 1))

	def test_a_year_only_series(self):
		"""Attendance and Leave Application both look like this."""
		self.assertEqual(self.split("HR-ATT-2026-12540"), ("HR-ATT-2026-", 12540))

	def test_the_trailing_digits_are_the_counter_not_the_year(self):
		"""HR-LAP-2026-00311 must not be read as prefix 'HR-LAP-' counter 2026.

		Winding the counter to 2026 would leave 00311 free and re-collide."""
		self.assertEqual(self.split("HR-LAP-2026-00311"), ("HR-LAP-2026-", 311))

	def test_a_name_with_no_trailing_number_is_not_a_series(self):
		"""Employee names on this fork are often hash- or slug-shaped. Inventing
		a counter for them would write junk rows into tabSeries."""
		self.assertIsNone(self.split("HR-EMP-ALICE"))

	def test_a_name_that_is_all_digits_is_not_a_series(self):
		"""No prefix means no series to advance."""
		self.assertIsNone(self.split("000123"))

	def test_a_hash_named_row_is_not_mistaken_for_a_series(self):
		"""The defect that made deriving from meta necessary.

		The first version split any name at its last non-digit, so the hash-named
		row `77r5o9d1b4` became prefix `77r5o9d1b` counter 4 and got WRITTEN into
		tabSeries. Caught on a bench, by reading what the patch actually did.
		Leave Ledger Entry and Employee both autoname to hashes."""
		for hashish in ("77r5o9d1b4", "a1b2c3d4e5", "9f8e7d6c5b4"):
			self.assertIsNone(self.split(hashish), f"{hashish} is a hash, not a series")

	def test_a_name_from_a_different_doctypes_series_does_not_match(self):
		"""Matchers are per doctype. Advancing another doctype's counter from
		this one's rows would move a number nobody asked about."""
		self.assertIsNone(self.split("HR-SHA-26-08-00012"))

	def test_leading_zeros_are_preserved_in_the_prefix_split(self):
		prefix, n = self.split("EMP-CKIN-08-2026-000042")
		self.assertEqual(prefix, "EMP-CKIN-08-2026-")
		self.assertEqual(n, 42)


class TestItOnlyEverMovesForward(unittest.TestCase):
	"""The direction is the whole safety property.

	A hub that has issued 000500 locally and then receives a late mirrored
	000003 must stay at 500. Winding back would free 000004..000500 for reissue
	and recreate the exact collision in the other direction — this time
	overwriting rows that already exist rather than failing loudly."""

	def setUp(self):
		self.tree = ast.parse(SOURCE.read_text())
		self.fn = next(
			(
				n
				for n in ast.walk(self.tree)
				if isinstance(n, ast.FunctionDef) and n.name == "advance_series_past"
			),
			None,
		)
		self.assertIsNotNone(self.fn, "runner.advance_series_past is missing")

	def test_it_compares_against_the_current_value(self):
		"""Read from the AST: a text search would match the docstring above,
		which spells out the rule it is supposed to be checking. That false pass
		has shipped twice in this project already."""
		called = {
			n.func.attr
			for n in ast.walk(self.fn)
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		}
		self.assertIn(
			"get_current_value",
			called,
			"advance_series_past must read the counter before writing it",
		)
		self.assertIn("update_counter", called)

	def test_the_write_is_guarded_by_a_comparison(self):
		compares = [n for n in ast.walk(self.fn) if isinstance(n, ast.Compare)]
		self.assertTrue(compares, "nothing compares the new value against the old one")


class TestTheSyncCallsIt(unittest.TestCase):
	def test_the_row_writer_records_the_names_it_forced(self):
		tree = ast.parse(SOURCE.read_text())
		fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "sync_doctype")
		called = {n.func.id for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
		self.assertIn(
			"advance_series_past",
			called,
			"a doctype can finish syncing without its counter being moved",
		)


if __name__ == "__main__":
	unittest.main()

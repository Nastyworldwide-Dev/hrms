"""Parity reporting — the cutover gate.

Cutover is authorised by a number, so these tests guard the number's meaning.
The properties that matter are the pessimistic ones: an unreachable doctype
must never read as "in parity", and a variance must reset the clean-run streak
rather than being averaged away.

Bench-free. `frappe` is not importable outside a bench and importing
`hrms.sync.parity` normally drags in the whole package, so the module is loaded
straight from its file with a stub `frappe` in `sys.modules`. Run as a FILE:

    python3 hrms/tests/test_sync_parity.py
"""

import importlib.util
import pathlib
import sys
import types
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = HRMS_ROOT / "sync" / "parity.py"


class _FakeDB:
	def __init__(self, counts=None):
		# counts: {(doctype, frozenset(filters.items())): n}
		self.counts = counts or {}
		self.calls = []

	def count(self, doctype, filters=None):
		self.calls.append((doctype, dict(filters or {})))
		return self.counts.get(doctype, 0)


def _load(fake_db):
	frappe_stub = types.ModuleType("frappe")
	frappe_stub.db = fake_db
	frappe_stub.whitelist = lambda *a, **kw: (lambda fn: fn)
	frappe_stub.only_for = lambda *a, **kw: None
	saved = sys.modules.get("frappe")
	sys.modules["frappe"] = frappe_stub
	try:
		spec = importlib.util.spec_from_file_location("_parity_under_test", MODULE_PATH)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		if saved is not None:
			sys.modules["frappe"] = saved
		else:
			del sys.modules["frappe"]
	return module


class _FakeClient:
	def __init__(self, counts, fail=None):
		self.instance_name = "nasty-live"
		self._counts = counts
		self._fail = fail or set()
		self.calls = []

	def count(self, doctype, filters=None):
		self.calls.append((doctype, filters))
		if doctype in self._fail:
			raise RuntimeError("remote unreachable")
		return self._counts.get(doctype, 0)


class TestCompareDoctype(unittest.TestCase):
	def test_equal_counts_are_in_parity(self):
		mod = _load(_FakeDB({"Employee": 10}))
		line = mod.compare_doctype(_FakeClient({"Employee": 10}), "Employee")
		self.assertTrue(line.in_parity)
		self.assertEqual(line.delta, 0)

	def test_missing_rows_locally_give_positive_delta(self):
		mod = _load(_FakeDB({"Employee": 7}))
		line = mod.compare_doctype(_FakeClient({"Employee": 10}), "Employee")
		self.assertEqual(line.delta, 3)
		self.assertFalse(line.in_parity)

	def test_local_count_only_counts_mirrored_rows(self):
		"""This site also holds its own greenfield companies — they must not inflate parity."""
		db = _FakeDB({"Employee": 5})
		mod = _load(db)
		mod.compare_doctype(_FakeClient({"Employee": 5}), "Employee")
		_, filters = db.calls[-1]
		self.assertEqual(filters.get("synced_from_instance"), "nasty-live")

	def test_company_filter_reaches_both_sides(self):
		db = _FakeDB({"Employee": 3})
		mod = _load(db)
		client = _FakeClient({"Employee": 3})
		mod.compare_doctype(client, "Employee", company="NCIG")
		self.assertEqual(client.calls[-1][1], {"company": "NCIG"})
		self.assertEqual(db.calls[-1][1].get("company"), "NCIG")

	def test_remote_failure_is_reported_not_raised(self):
		mod = _load(_FakeDB({"Employee": 5}))
		line = mod.compare_doctype(_FakeClient({}, fail={"Employee"}), "Employee")
		self.assertIsNotNone(line.error)
		self.assertFalse(line.in_parity, "an errored comparison must never read as in-parity")


class TestParityReport(unittest.TestCase):
	def test_all_equal_is_in_parity(self):
		counts = dict.fromkeys(("Employee", "Attendance"), 4)
		mod = _load(_FakeDB(counts))
		report = mod.parity_report(_FakeClient(counts), doctypes=["Employee", "Attendance"])
		self.assertTrue(report["in_parity"])
		self.assertEqual(report["mismatched"], [])

	def test_one_mismatch_fails_the_whole_report(self):
		mod = _load(_FakeDB({"Employee": 4, "Attendance": 1}))
		report = mod.parity_report(
			_FakeClient({"Employee": 4, "Attendance": 9}), doctypes=["Employee", "Attendance"]
		)
		self.assertFalse(report["in_parity"])
		self.assertEqual(report["mismatched"], ["Attendance"])

	def test_unreachable_doctype_never_reports_clean(self):
		mod = _load(_FakeDB({"Employee": 4}))
		report = mod.parity_report(
			_FakeClient({"Employee": 4}, fail={"Attendance"}),
			doctypes=["Employee", "Attendance"],
		)
		self.assertFalse(report["in_parity"])
		self.assertIn("Attendance", report["errored"])


class TestTheGateComparesLikeForLike(unittest.TestCase):
	"""The remote side must be counted under the same scope the sync pulls under.

	verifica-live, 2026-08-17: the report read `Employee 308 on source, 116 here,
	192 missing`. The source holds 308 employees across ten companies and every
	status; the sync is scoped to the seven companies this instance serves. The two
	numbers were never comparable, so the delta was noise and the gate could never
	reach zero however healthy the mirror was.

	A gate that cannot reach zero is worse than no gate: it reports a permanent
	variance that trains everyone to ignore it.
	"""

	def test_the_remote_count_honours_an_explicit_filter(self):
		db = _FakeDB({"Employee": 116})
		mod = _load(db)
		client = _FakeClient({"Employee": 116})

		mod.compare_doctype(client, "Employee", remote_filters={"company": ("in", ["Acme"])})

		self.assertEqual(client.calls[-1][1], {"company": ("in", ["Acme"])})

	def test_the_local_count_stays_keyed_on_provenance_alone(self):
		"""Local rows are already only the scoped ones — they carry the stamp
		BECAUSE the sync chose them. Filtering them again by company would drop
		mirrored rows whose doctype has no company field."""
		db = _FakeDB({"Employee": 116})
		mod = _load(db)

		mod.compare_doctype(
			_FakeClient({"Employee": 116}), "Employee", remote_filters={"company": ("in", ["Acme"])}
		)

		_, filters = db.calls[-1]
		self.assertEqual(filters, {"synced_from_instance": "nasty-live"})

	def test_a_scoped_comparison_can_reach_parity(self):
		"""The whole point: same scope on both sides, so zero is attainable."""
		mod = _load(_FakeDB({"Employee": 116}))
		line = mod.compare_doctype(
			_FakeClient({"Employee": 116}), "Employee", remote_filters={"company": ("in", ["Acme"])}
		)
		self.assertTrue(line.in_parity)
		self.assertEqual(line.delta, 0)


class TestCutoverReadiness(unittest.TestCase):
	def setUp(self):
		self.mod = _load(_FakeDB())

	def test_enough_consecutive_clean_runs_is_ready(self):
		runs = [{"in_parity": True}] * 4
		self.assertTrue(self.mod.is_cutover_ready(runs, required_clean_runs=4)["ready"])

	def test_too_few_clean_runs_is_not_ready(self):
		runs = [{"in_parity": True}] * 2
		self.assertFalse(self.mod.is_cutover_ready(runs, required_clean_runs=4)["ready"])

	def test_a_variance_resets_the_streak(self):
		# Clean for ages, then one bad run, then two clean: streak is 2, not 6.
		runs = [{"in_parity": True}] * 4 + [{"in_parity": False}] + [{"in_parity": True}] * 2
		result = self.mod.is_cutover_ready(runs, required_clean_runs=4)
		self.assertEqual(result["consecutive_clean_runs"], 2)
		self.assertFalse(result["ready"])

	def test_streak_counts_from_the_most_recent_run(self):
		# Most recent run failed — never ready, regardless of history.
		runs = [{"in_parity": True}] * 10 + [{"in_parity": False}]
		result = self.mod.is_cutover_ready(runs, required_clean_runs=1)
		self.assertEqual(result["consecutive_clean_runs"], 0)
		self.assertFalse(result["ready"])

	def test_no_runs_is_not_ready(self):
		self.assertFalse(self.mod.is_cutover_ready([], required_clean_runs=4)["ready"])


class TestGateCoversExactlyWhatIsMirrored(unittest.TestCase):
	"""The gate's doctype list must equal the runner's, or it lies in one of two ways.

	Report on something the runner never mirrors and the local count is always
	zero, so parity is unreachable and cutover never authorises. Omit something
	the runner does mirror and a failed sync for that doctype is invisible — the
	gate calls it clean. Both are silent, so this is pinned rather than trusted.
	"""

	def _tuple_from(self, path, name):
		"""Read a module-level tuple without importing the module (no bench needed)."""
		import ast

		tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))
		for node in tree.body:
			if isinstance(node, ast.Assign) and any(
				isinstance(t, ast.Name) and t.id == name for t in node.targets
			):
				return tuple(ast.literal_eval(node.value))
		raise AssertionError(f"{name} not found in {path}")

	def test_parity_and_runner_agree(self):
		"""The gate counts local rows BY THE PROVENANCE STAMP, so it must track the
		stamped doctypes — not everything a run pulls.

		`DEFAULT_SYNC_DOCTYPES` also carries the create-only masters (Leave Type,
		Designation, ...), which are HR-owned here and deliberately unstamped.
		Comparing against that list would ask parity to count rows that carry no
		stamp, and every run would report a variance that no cutover could clear.
		"""
		gate = self._tuple_from(HRMS_ROOT / "sync" / "parity.py", "MIRRORED_DOCTYPES")
		stamped = self._tuple_from(HRMS_ROOT / "sync" / "runner.py", "STAMPED_DOCTYPES")
		self.assertEqual(
			sorted(gate),
			sorted(stamped),
			"parity.MIRRORED_DOCTYPES and runner.STAMPED_DOCTYPES have drifted; "
			"the cutover gate must cover exactly what the sync stamps",
		)


class TestTheGateIsReachable(unittest.TestCase):
	"""The number that authorises cutover has to be obtainable by the person who
	needs it.

	This module's whole purpose is to answer "did the data actually land?" — and
	`parity_report` was whitelisted nowhere and had no button, so the only way to
	get the answer was a bench console. An operator staring at an empty leave
	balance could not tell a sync that never ran from one that ran and wrote
	nothing.
	"""

	def test_parity_check_is_whitelisted(self):
		import ast

		tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
		functions = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
		self.assertIn("parity_check", functions, "parity has no whitelisted entry point")

		decorators = [
			d for d in functions["parity_check"].decorator_list
		]
		self.assertTrue(decorators, "parity_check is not whitelisted")

	def test_parity_check_is_read_only_on_both_sides(self):
		"""It compares; it must never reconcile. A gate that writes is not a gate."""
		source = MODULE_PATH.read_text(encoding="utf-8")
		for writer in ("set_value", "insert(", "delete_doc", "db.sql"):
			self.assertNotIn(writer, source, f"parity must not write: found {writer}")

	def test_it_refuses_callers_who_are_not_hr(self):
		source = MODULE_PATH.read_text(encoding="utf-8")
		self.assertIn("only_for", source)


if __name__ == "__main__":
	unittest.main()

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


if __name__ == "__main__":
	unittest.main()

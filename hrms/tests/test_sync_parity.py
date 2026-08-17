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


def _install_runner(frappe_stub):
	"""Make the REAL `hrms.sync.runner` importable under the stub.

	`parity._count_remote` splits an over-long filter using the runner's own
	splitter, imported rather than restated — the gate counting under different
	rules from the sync it grades is the class of bug this file exists to catch.
	Stubbing the splitter here would test a copy and prove nothing.
	"""
	import logging

	frappe_stub._ = lambda text: text
	frappe_stub.logger = lambda *a, **kw: logging.getLogger("hrms-test")
	frappe_stub.flags = types.SimpleNamespace()
	frappe_stub.get_all = lambda *a, **kw: []
	frappe_stub.get_doc = lambda *a, **kw: None
	utils = types.ModuleType("frappe.utils")
	utils.now_datetime = lambda: None
	frappe_stub.utils = utils
	sys.modules["frappe.utils"] = utils

	spec = importlib.util.spec_from_file_location("hrms.sync.runner", HRMS_ROOT / "sync" / "runner.py")
	runner = importlib.util.module_from_spec(spec)
	sys.modules["hrms.sync.runner"] = runner
	spec.loader.exec_module(runner)


def _load(fake_db):
	frappe_stub = types.ModuleType("frappe")
	frappe_stub.db = fake_db
	frappe_stub.whitelist = lambda *a, **kw: lambda fn: fn
	frappe_stub.only_for = lambda *a, **kw: None
	saved = sys.modules.get("frappe")
	sys.modules["frappe"] = frappe_stub
	_install_runner(frappe_stub)
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


class TestADoctypeTheSourceDoesNotHave(unittest.TestCase):
	"""404 from the source is a version gap, not a variance.

	verifica-live: `Holiday List Assignment` does not exist on nasty-sg-dev, which
	runs an older HRMS. Reported as an error the gate stays red for ever — and a
	gate that can never go green is one nobody reads.

	Zero there and zero here IS parity. Rows here with none there is a real
	divergence and must still show.
	"""

	def _absent_client(self):
		class _Absent(_FakeClient):
			def count(self, doctype, filters=None):
				self.calls.append((doctype, filters))
				error = RuntimeError("remote rejected the read (status=404)")
				error.status_code = 404
				raise error

		return _Absent({})

	def test_absent_there_and_empty_here_is_parity(self):
		mod = _load(_FakeDB({"Holiday List Assignment": 0}))

		line = mod.compare_doctype(self._absent_client(), "Holiday List Assignment")

		self.assertIsNone(line.error, "a version gap must not read as an error")
		self.assertTrue(line.in_parity)

	def test_absent_there_but_rows_here_is_still_a_divergence(self):
		"""Rows mirrored before the source lost the doctype are a real finding."""
		mod = _load(_FakeDB({"Holiday List Assignment": 12}))

		line = mod.compare_doctype(self._absent_client(), "Holiday List Assignment")

		self.assertFalse(line.in_parity)
		self.assertEqual(line.delta, -12)

	def test_a_real_remote_failure_is_still_an_error(self):
		mod = _load(_FakeDB({"Employee": 5}))
		line = mod.compare_doctype(_FakeClient({}, fail={"Employee"}), "Employee")
		self.assertIsNotNone(line.error)


class TestALongFilterIsCountedInChunks(unittest.TestCase):
	"""SYNC-00057 completed cleanly and parity still could not count check-ins:

	    Employee Checkin: remote rejected the read (status=400)

	Employee Checkin has no company field, so both sides scope it by the mirrored
	employee list — and at 289 names that list overruns the request line. The SYNC
	learned to split it; the GATE did not, so the one doctype whose scope needs
	splitting was the one the gate could never measure.

	Fixing it in one place and not the other is how a mirror ends up healthier than
	the instrument watching it.
	"""

	def test_a_long_filter_is_summed_across_requests(self):
		mod = _load(_FakeDB({"Employee Checkin": 1474}))
		names = [f"HR-EMP-{i:05d}" for i in range(250)]

		class _Chunked(_FakeClient):
			def count(self, doctype, filters=None):
				self.calls.append((doctype, filters))
				# Refuse anything that would overrun the request line, as the
				# remote's proxy does.
				if filters and len(filters["employee"][1]) > 100:
					error = RuntimeError("remote rejected the read (status=400)")
					error.status_code = 400
					raise error
				return len(filters["employee"][1])

		client = _Chunked({})
		line = mod.compare_doctype(client, "Employee Checkin", remote_filters={"employee": ("in", names)})

		self.assertIsNone(line.error, "an over-long filter must be split, not reported as failure")
		self.assertEqual(line.remote, 250, "every chunk must be counted, and summed")
		self.assertGreater(len(client.calls), 1)

	def test_a_short_filter_is_still_one_request(self):
		mod = _load(_FakeDB({"Employee": 5}))
		client = _FakeClient({"Employee": 5})

		mod.compare_doctype(client, "Employee", remote_filters={"company": ("in", ["Acme"])})

		self.assertEqual(len(client.calls), 1)


class TestWhatElseIsOnTheSource(unittest.TestCase):
	"""Turns "what are we still not bringing across?" into a number.

	Every gap this migration has hit was argued about before it was measured —
	payroll most of all. The mirror carries 13 doctypes; the source has more, and
	the only honest way to decide whether a doctype matters is to ask how many rows
	it holds over there. A doctype with 0 rows is not a gap, however important it
	sounds.

	Read-only, and tolerant: a source that lacks a doctype answers 404, and a user
	who cannot read it answers 403. Neither is a failure of the survey — both are
	part of the answer.
	"""

	def test_it_counts_only_doctypes_the_mirror_does_not_carry(self):
		mod = _load(_FakeDB())
		self.assertTrue(mod.UNMIRRORED_CANDIDATES)
		for doctype in mod.UNMIRRORED_CANDIDATES:
			self.assertNotIn(doctype, mod.MIRRORED_DOCTYPES)

	def test_a_doctype_with_rows_is_reported_as_a_gap(self):
		mod = _load(_FakeDB())
		client = _FakeClient({"Salary Structure": 12})

		report = mod.source_inventory(client, doctypes=["Salary Structure"])

		self.assertEqual(report["has_data"], [{"doctype": "Salary Structure", "rows": 12}])
		self.assertEqual(report["empty"], [])

	def test_an_empty_doctype_is_not_a_gap(self):
		"""The whole point — payroll nobody uses is not payroll we have to mirror."""
		mod = _load(_FakeDB())

		report = mod.source_inventory(_FakeClient({"Salary Slip": 0}), doctypes=["Salary Slip"])

		self.assertEqual(report["has_data"], [])
		self.assertEqual(report["empty"], ["Salary Slip"])

	def test_a_doctype_the_source_lacks_is_reported_separately(self):
		"""Not a gap and not an error: that source simply has no such concept."""
		mod = _load(_FakeDB())

		class _Absent(_FakeClient):
			def count(self, doctype, filters=None):
				error = RuntimeError("remote rejected the read (status=404)")
				error.status_code = 404
				raise error

		report = mod.source_inventory(_Absent({}), doctypes=["Gratuity"])

		self.assertEqual(report["not_on_source"], ["Gratuity"])

	def test_an_unreadable_doctype_is_named_rather_than_swallowed(self):
		mod = _load(_FakeDB())

		report = mod.source_inventory(_FakeClient({}, fail={"Salary Slip"}), doctypes=["Salary Slip"])

		self.assertEqual(len(report["unreadable"]), 1)
		self.assertEqual(report["unreadable"][0]["doctype"], "Salary Slip")


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

		decorators = [d for d in functions["parity_check"].decorator_list]
		self.assertTrue(decorators, "parity_check is not whitelisted")

	def test_parity_check_is_read_only_on_both_sides(self):
		"""It compares; it must never reconcile. A gate that writes is not a gate."""
		source = MODULE_PATH.read_text(encoding="utf-8")
		for writer in ("set_value", "insert(", "delete_doc", "db.sql"):
			self.assertNotIn(writer, source, f"parity must not write: found {writer}")

	def test_it_refuses_callers_who_are_not_hr(self):
		source = MODULE_PATH.read_text(encoding="utf-8")
		self.assertIn("only_for", source)


class TestTheTwoListsCannotOverlap(unittest.TestCase):
	"""`UNMIRRORED_CANDIDATES` is hand-written, and it answers "what is on the
	source that we do NOT bring across?". A doctype that appears in it AND in the
	runner's sync list makes that answer a lie in the most expensive direction:
	the survey reports it as an outstanding gap, so someone goes and re-solves a
	problem that is already solved.

	This is not hypothetical — the leave chain sat in both lists the moment it was
	added to the runner, which is exactly when the survey would have started
	reporting 936 Leave Applications as missing while mirroring all 936.
	"""

	def setUp(self):
		self.parity = _load(_FakeDB())
		self.runner = sys.modules["hrms.sync.runner"]

	def test_no_doctype_is_both_mirrored_and_listed_as_unmirrored(self):
		overlap = sorted(set(self.parity.UNMIRRORED_CANDIDATES) & set(self.runner.DEFAULT_SYNC_DOCTYPES))
		self.assertEqual(
			overlap,
			[],
			"these are mirrored, so the survey must stop calling them gaps: " + ", ".join(overlap),
		)

	def test_the_lists_are_both_populated(self):
		"""Guards the guard — two empty sets never overlap."""
		self.assertGreater(len(self.parity.UNMIRRORED_CANDIDATES), 10)
		self.assertGreater(len(self.runner.DEFAULT_SYNC_DOCTYPES), 10)


if __name__ == "__main__":
	unittest.main()

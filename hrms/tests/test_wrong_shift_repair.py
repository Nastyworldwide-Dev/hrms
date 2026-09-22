"""The wrong-shift repair: a shift that belongs to two people, held by everyone.

Owner, 22 September 2026: "if the fix on X isnt Y or Z then X should revert to
its original shift. because 7-3.30 shift only belongs to Y and Z only. the rest
has their own original shift assigned."

The rule is a definition, not a heuristic: a punch stamped to a guarded shift
whose employee is not one of its owners is wrong whatever produced it, and the
roster says what it should be instead.

What is pinned here:

* WHO — every employee carrying a punch on a guarded shift they do not own, and
  nobody else. The two owners are never selected;
* the window is read against the punch's CLOCK time, never its shift stamp —
  the stamp is the thing under suspicion;
* the repair goes through `restamp`, the one resolution, so it cannot drift
  from the rule the engine applies to a fresh tap;
* the two powers this job carries and no other path does — ERP-pulled punches
  are in scope (`mirrored_ok`) and the re-mark carries HR's authority
  (`authoritative`, owner option B) — and that BOTH are off by default
  everywhere else;
* money is never waived: `authoritative` maps to hr_asked/requests_ok, and
  neither of those touches the financial hold;
* it never raises, is idempotent, and one employee's failure does not end the
  run.

    PYTHONPATH=. python3 hrms/tests/test_wrong_shift_repair.py
"""

import pathlib
import re
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path[:0] = [
	str(pathlib.Path(__file__).resolve().parents[2]),
	str(pathlib.Path(__file__).resolve().parent),
]
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.utils import restamp as restamp_mod
from hrms.utils import wrong_shift_repair as repair


class TestWhoIsSelected(unittest.TestCase):
	def test_only_the_people_who_do_not_own_the_shift(self):
		seen = {}

		def _get_all(doctype, filters=None, **kw):
			if doctype == "Shift Assignment":
				return [{"employee": "HR-EMP-00028"}, {"employee": "HR-EMP-00063"}]
			seen.update(filters)
			return [{"employee": "HR-EMP-00101"}, {"employee": "HR-EMP-00102"}, {"employee": "HR-EMP-00101"}]

		with patch.object(frappe, "get_all", _get_all):
			found = repair.employees_holding_a_shift_they_do_not_own("2026-08-01", "2026-09-21")
		self.assertEqual(found, ["HR-EMP-00101", "HR-EMP-00102"], "deduplicated, ordered")
		self.assertEqual(
			seen["employee"],
			("not in", ["HR-EMP-00028", "HR-EMP-00063"]),
			"the two owners are excluded by the query, not filtered afterwards",
		)
		self.assertEqual(seen["shift"], "7PM - 3.30AM")

	def test_the_window_is_read_against_the_clock_not_the_stamp(self):
		"""Selecting by `shift_start` would trust the value being repaired: a
		punch whose stamp threw it onto the wrong DAY could fall outside a
		window its own clock time is inside."""
		seen = {}

		def _get_all(doctype, filters=None, **kw):
			if doctype == "Shift Assignment":
				return [{"employee": "HR-EMP-00028"}, {"employee": "HR-EMP-00063"}]
			seen.update(filters)
			return []

		with patch.object(frappe, "get_all", _get_all):
			repair.employees_holding_a_shift_they_do_not_own("2026-08-01", "2026-09-21")
		self.assertIn("time", seen)
		self.assertNotIn("shift_start", seen)
		self.assertEqual(seen["time"][1][0], "2026-08-01 00:00:00")
		self.assertEqual(seen["time"][1][1], "2026-09-21 23:59:59")

	def test_nobody_wrongly_stamped_means_nothing_to_do(self):
		with patch.object(frappe, "get_all", return_value=[]):
			self.assertEqual(repair.employees_holding_a_shift_they_do_not_own("2026-08-01", "2026-09-21"), [])

	def test_a_roster_that_has_grown_a_third_owner_refuses_the_shift(self):
		"""The owner list is a constant because the roster is what a stray
		assignment corrupted. But it was true when he read it, and this job
		runs later. A third person legitimately assigned the shift meanwhile
		is an OWNER, and reverting their punches would be this job committing
		the defect it exists to repair. Doing nothing is recoverable."""
		calls = []

		def _get_all(doctype, filters=None, **kw):
			calls.append(doctype)
			if doctype == "Shift Assignment":
				return [
					{"employee": "HR-EMP-00028"},
					{"employee": "HR-EMP-00063"},
					{"employee": "HR-EMP-00999"},
				]
			return [{"employee": "HR-EMP-00101"}]

		with patch.object(frappe, "get_all", _get_all), patch.object(frappe, "log_error") as logged:
			found = repair.employees_holding_a_shift_they_do_not_own("2026-08-01", "2026-09-21")
		self.assertEqual(found, [], "nothing is repaired against a stale owner list")
		self.assertNotIn("Employee Checkin", calls, "the punches are not even read")
		logged.assert_called_once()
		self.assertIn("HR-EMP-00999", logged.call_args.kwargs["message"])

	def test_a_roster_that_lost_an_owner_still_repairs(self):
		"""Fewer owners than the constant is not drift that can hurt anyone:
		the missing person is simply never selected, because the query excludes
		every name in the constant. Refusing there would strand the repair on a
		site where one of the two has since left."""
		# Asserting an empty RESULT is not enough — a refusal returns empty too
		# (and did, under a mutant that made the drift check symmetric). What
		# this pins is that the punches were READ.
		calls = []

		def _get_all(doctype, filters=None, **kw):
			calls.append(doctype)
			if doctype == "Shift Assignment":
				return [{"employee": "HR-EMP-00028"}]
			return [{"employee": "HR-EMP-00101"}]

		with patch.object(frappe, "get_all", _get_all), patch.object(frappe, "log_error") as logged:
			found = repair.employees_holding_a_shift_they_do_not_own("2026-08-01", "2026-09-21")
		self.assertEqual(found, ["HR-EMP-00101"], "the repair runs as usual")
		self.assertIn("Employee Checkin", calls)
		logged.assert_not_called()

	def test_drift_is_judged_on_submitted_assignments_only(self):
		seen = {}

		def _get_all(doctype, filters=None, **kw):
			if doctype == "Shift Assignment":
				seen.update(filters)
			return []

		with patch.object(frappe, "get_all", _get_all):
			repair.roster_drifted("7PM - 3.30AM", ("HR-EMP-00028", "HR-EMP-00063"))
		self.assertEqual(seen["docstatus"], 1, "a draft or cancelled assignment owns nothing")

	def test_the_guarded_shift_names_its_two_owners(self):
		self.assertEqual(repair.GUARDED_SHIFTS, {"7PM - 3.30AM": ("HR-EMP-00028", "HR-EMP-00063")})


class TestTheRepairGoesThroughTheOneResolution(unittest.TestCase):
	def _run(self, employees, restamp_fn):
		with (
			patch.object(repair, "employees_holding_a_shift_they_do_not_own", return_value=employees),
			patch.object(repair, "restamp", restamp_fn),
			patch.object(frappe.db, "commit"),
			patch.object(frappe.db, "rollback"),
			patch.object(frappe, "log_error"),
		):
			return repair.run_repair("2026-08-01", "2026-09-21")

	def test_it_repairs_the_erp_punches_and_overrides_hr(self):
		"""The two powers the owner granted, passed EXPLICITLY. Without
		`mirrored_ok` the whole 1 Aug - 4 Sep window is skipped (every punch
		there came from the old ERP); without `authoritative` every day HR had
		already touched by hand is held, which is the half of the damage the
		owner asked for in the same breath."""
		calls = []

		def _restamp(employee, from_date, to_date, **kw):
			calls.append((employee, kw))
			return {"planned": [{"name": "CK-1"}], "released": ["CK-1"], "days": ["2026-08-11"]}

		out = self._run(["HR-EMP-00101"], _restamp)
		_, kw = calls[0]
		self.assertTrue(kw["mirrored_ok"], "ERP-pulled punches are in scope (owner, 22 Sep 2026)")
		self.assertTrue(kw["authoritative"], "a day HR keyed on a wrong stamp is rebuilt (option B)")
		self.assertFalse(kw["dry_run"], "the repair WRITES; a dry run repairs nothing")
		self.assertEqual(out["punches"], 1)
		self.assertEqual(out["released"], 1)

	def test_an_employee_who_throws_does_not_end_the_run(self):
		def _restamp(employee, from_date, to_date, **kw):
			if employee == "HR-EMP-00101":
				raise ValueError("boom")
			return {"planned": [], "released": [], "days": []}

		out = self._run(["HR-EMP-00101", "HR-EMP-00102"], _restamp)
		self.assertEqual(out["employees"], 2, "both were attempted")
		self.assertEqual(out["failed"], ["HR-EMP-00101"])

	def test_a_second_run_writes_nothing(self):
		out = self._run(["HR-EMP-00101"], lambda *a, **kw: {"planned": [], "released": [], "days": []})
		self.assertEqual(out["punches"], 0)

	def test_the_window_ends_yesterday_when_nobody_says_otherwise(self):
		"""The patch calls run_repair() with no dates, so this is the only
		branch the real one-time job ever takes."""
		seen = {}

		def _at_risk(from_date, to_date):
			seen["from"], seen["to"] = from_date, to_date
			return []

		with (
			patch.object(repair, "employees_holding_a_shift_they_do_not_own", _at_risk),
			patch.object(repair, "nowdate", lambda: "2026-09-22"),
		):
			repair.run_repair()
		self.assertEqual(str(seen["from"]), repair.FROM_DATE)
		self.assertEqual(str(seen["to"]), "2026-09-21", "today is still being punched")


class TestThePowersAreOffEverywhereElse(unittest.TestCase):
	"""A flag this job needs must not become the new default for the nightly
	job, the roster-driven re-stamp, or HR's preview."""

	def setUp(self):
		self.restamp_src = pathlib.Path(restamp_mod.__file__).read_text()

	def test_both_powers_default_to_off(self):
		self.assertIn("mirrored_ok=False", self.restamp_src)
		self.assertIn("authoritative=False", self.restamp_src)

	def test_mirrored_punches_are_still_excluded_unless_asked(self):
		self.assertIn('filters["synced_from_instance"] = ("is", "not set")', self.restamp_src)
		self.assertIn("if not mirrored_ok:", self.restamp_src)

	def test_the_write_is_fenced_the_same_way_it_was_read(self):
		"""The `where` of the update must carry the same mirrored fence as the
		read, or a run WITHOUT the power could still write a mirrored punch it
		matched by name."""
		where = self.restamp_src.split("where = {", 1)[1].split("if not dry_run:", 1)[0]
		self.assertIn('where["synced_from_instance"] = ("is", "not set")', where)
		self.assertIn("if not mirrored_ok:", where)

	def test_only_this_job_asks_for_them(self):
		# Scoped to calls of THIS function: `attendance_fix_day._tap` has a
		# parameter of the same name for one punch HR is looking at, which is a
		# different permission and not this grant.
		root = pathlib.Path(restamp_mod.__file__).resolve().parents[1]
		askers = set()
		for path in root.rglob("*.py"):
			if "/tests/" in str(path):
				continue
			text = path.read_text(encoding="utf-8")
			for call in re.finditer(r"restamp\(\s*([^)]*)\)", text, re.S):
				if "mirrored_ok=True" in call.group(1) or "authoritative=True" in call.group(1):
					askers.add(path.name)
		self.assertEqual(askers, {"wrong_shift_repair.py"}, "one caller holds the owner's grant")

	def test_the_preview_never_carries_them(self):
		preview = self.restamp_src.split("def preview(", 1)[1].split("\n\n\n", 1)[0]
		self.assertNotIn("mirrored_ok", preview)
		self.assertNotIn("authoritative", preview)


class TestMoneyIsNeverWaived(unittest.TestCase):
	def test_authoritative_maps_to_the_two_hr_flags_and_no_third(self):
		src = pathlib.Path(restamp_mod.__file__).read_text()
		self.assertIn("hr_asked=authoritative, requests_ok=authoritative", src)

	def test_the_financial_hold_is_not_reachable_by_either_flag(self):
		"""`protected_reason` returns the financial hold AFTER both flags have
		had their say, and neither is consulted on that branch."""
		from hrms.utils import attendance_recovery as rec

		src = pathlib.Path(rec.__file__).read_text()
		body = src.split("def protected_reason(", 1)[1].split("\n\n\n", 1)[0]
		financial = body.split("if financial:", 1)[1]
		self.assertNotIn("hr_asked", financial)
		self.assertNotIn("requests_ok", financial)


class TestTheMigrateJustAsksForIt(unittest.TestCase):
	def test_the_patch_only_enqueues(self):
		from hrms.patches.v16_0 import run_wrong_shift_repair_once as patch_mod

		with patch.object(frappe, "enqueue") as enqueue:
			patch_mod.execute()
		enqueue.assert_called_once()
		self.assertEqual(enqueue.call_args.kwargs["queue"], "long")
		self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])
		self.assertEqual(enqueue.call_args.args[0], "hrms.utils.wrong_shift_repair.run_repair")

	def test_a_failed_enqueue_never_fails_the_migrate(self):
		from hrms.patches.v16_0 import run_wrong_shift_repair_once as patch_mod

		with (
			patch.object(frappe, "enqueue", side_effect=RuntimeError("no redis")),
			patch.object(frappe, "log_error") as log_error,
		):
			patch_mod.execute()  # must not raise
		log_error.assert_called_once()

	def test_the_patch_is_registered(self):
		line = "hrms.patches.v16_0.run_wrong_shift_repair_once"
		text = (pathlib.Path(__file__).resolve().parents[1] / "patches.txt").read_text()
		self.assertIn(line, text, "a patch nobody lists never runs")

	def test_it_runs_after_the_grace_repair(self):
		"""The grace fix re-resolves; this one overrules. Ordering them the
		other way would let the grace pass re-mark a day from stamps this job
		is about to change."""
		text = (pathlib.Path(__file__).resolve().parents[1] / "patches.txt").read_text()
		lines = [ln.split("#")[0].strip() for ln in text.splitlines()]
		self.assertLess(
			lines.index("hrms.patches.v16_0.run_grace_restamp_repair_once"),
			lines.index("hrms.patches.v16_0.run_wrong_shift_repair_once"),
		)


class TestTheAuthorityTravelsWithTheJob(unittest.TestCase):
	def test_the_queued_remark_carries_the_flags(self):
		from hrms.utils import day_remark

		src = pathlib.Path(day_remark.__file__).read_text()
		self.assertIn("hr_asked=hr_asked", src)
		self.assertIn("requests_ok=requests_ok", src)

	def test_two_authorities_are_two_jobs(self):
		"""Deduplicating an authoritative re-mark into a plain one already
		waiting would answer the stronger question with the weaker one. The
		PLAIN id keeps its old shape, so a job queued before this deploy still
		deduplicates against the ones that follow it."""
		from hrms.utils import day_remark

		src = pathlib.Path(day_remark.__file__).read_text()
		self.assertIn(
			'job_id = f"day-remark::{employee}::{day}" + (f"::{authority}" if authority else "")', src
		)
		self.assertIn('(("hr", hr_asked), ("req", requests_ok))', src)

	def test_a_queued_remark_is_never_inline(self):
		"""`remark_day` defaults `inline` to `hr_asked`, and an inline unit does
		not retry a deadlock. At the worker that would surface as a lost
		transaction instead of a retry."""
		from hrms.utils import day_remark

		src = pathlib.Path(day_remark.__file__).read_text()
		enqueue = src.split("def _enqueue(", 1)[1].split("\n\n", 1)[0]
		self.assertIn("inline=False", enqueue)


if __name__ == "__main__":
	unittest.main()

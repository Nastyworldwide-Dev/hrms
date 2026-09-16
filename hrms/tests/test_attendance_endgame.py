"""The endgame repairs the month by itself after deploy — Nabil, 16 Sep 2026.

"too much mechanical work for us and for HR — it should be done automatically by
the system at once, except the relinking screen I asked for."

So one background job does the whole repair in a fixed order, resuming safely,
and HR reads one summary at the end. The only thing left for a person is the Fix
Day screen. These tests hold that promise to the fixed order, to resuming after a
kill, to the stop switch, to one summary per run, to the run id on every log
entry, and to an undo that reverses its own run and nothing else.

	PYTHONPATH=. python3 hrms/tests/test_attendance_endgame.py
"""

import json
import pathlib
import sys
import unittest
from datetime import date
from types import SimpleNamespace
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

from hrms.utils import attendance_endgame as eg

TODAY = "2026-09-16"
YESTERDAY = "2026-09-15"
#: 1 Aug → 15 Sep in 31-day chunks.
CHUNKS = [("2026-08-01", "2026-08-31"), ("2026-09-01", "2026-09-15")]


def _settings(values):
	"""HR Settings holding exactly `values`; anything else is an absent field."""
	return lambda doctype: SimpleNamespace(get=lambda key, default=None: values.get(key, default))


class _Case(unittest.TestCase):
	"""Every outside worker is a recorder: the orchestrator's own order is the subject."""

	def setUp(self):
		self.calls = []
		self.raises = {}
		self.defaults = {}
		self.db = MagicMock()
		self.db.exists.return_value = None
		self.db.get_default.side_effect = lambda key: self.defaults.get(key)
		self.db.set_default.side_effect = lambda key, value: self.defaults.__setitem__(key, value)
		self.notify = MagicMock()
		self.logged = []

		def log_error(title=None, message=None, **kwargs):
			self.logged.append((title, message))
			return SimpleNamespace(name="ERR-1")

		patches = [
			patch.object(frappe, "db", self.db),
			patch.object(frappe, "set_user", MagicMock(), create=True),
			patch.object(frappe, "log_error", log_error),
			patch.object(frappe, "get_single", _settings({}), create=True),
			patch.object(eg, "notify_hr", self.notify),
			patch.object(eg, "nowdate", lambda: TODAY),
			patch.object(eg.own, "relabel_system_rows", self._recorder("relabel", self._relabel)),
			patch.object(eg.backfill, "parity", self._recorder("parity", self._parity)),
			patch.object(eg.backfill, "backfill_punches", self._recorder("punches", self._punches)),
			patch.object(eg.auto, "_run", self._recorder("recovery", self._recovery)),
			patch.object(eg, "_recount_ot", self._recorder("ot", lambda *a, **k: {"done": [1, 2]})),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)

	def _recorder(self, name, inner):
		def call(*args, **kwargs):
			window = (str(args[0]), str(args[1])) if len(args) >= 2 else ()
			self.calls.append((name, *window))
			if name in self.raises:
				raise self.raises[name]
			return inner(*args, **kwargs)

		return call

	def _relabel(self, start, end, **kwargs):
		return {"ok": True, "changed": [{"attendance": "ATT-1"}], "counts": {}, "scanned": 3}

	def _parity(self, start, end, **kwargs):
		return {"counts": {"hub_missing_punches": 4}, "rows": []}

	def _punches(self, start, end, **kwargs):
		return {"inserted": [{"checkin": "CI-1"}], "rebuilt": [{"employee": "E1"}], "held_back": []}

	def _recovery(self, start, end, **kwargs):
		return {
			"from_date": str(start),
			"to_date": str(end),
			"steps": {"rebuild": {"done": 2, "held_back": 1, "needs_hr": 1, "on_purpose": 0}},
			"hr_days": 1,
			"protected_days": 3,
			"stopped_at": [],
		}

	def _steps(self, name):
		return [c for c in self.calls if c[0] == name]


class TestOrder(_Case):
	def test_each_step_covers_the_whole_window_before_the_next_one_starts(self):
		# The order is a pipeline, not a per-chunk loop: every row is relabelled
		# before a punch is copied, and the OT recount runs last of all, so it
		# prices every day the steps before it rebuilt.
		eg.run_endgame()
		order = [c[0] for c in self.calls if c[0] != "parity"]
		self.assertEqual(
			order,
			["relabel", "relabel", "punches", "punches", "recovery", "recovery", "ot", "ot"],
		)

	def test_the_window_starts_at_the_first_of_august_and_stops_at_yesterday(self):
		eg.run_endgame()
		self.assertEqual([(c[1], c[2]) for c in self._steps("relabel")], CHUNKS)
		self.assertEqual([(c[1], c[2]) for c in self._steps("recovery")], CHUNKS)

	def test_an_earlier_from_date_is_pulled_up_to_the_floor(self):
		eg.run_endgame(from_date="2026-07-01")
		self.assertEqual(self._steps("relabel")[0][1], "2026-08-01")

	def test_a_later_to_date_is_pulled_back_to_yesterday(self):
		eg.run_endgame(to_date="2026-12-31")
		self.assertEqual(self._steps("relabel")[-1][2], YESTERDAY)

	def test_the_punch_copy_never_reaches_the_cutover(self):
		# The hub owns everything from 4 Sep; the ERP owns 1 Aug → 3 Sep.
		eg.run_endgame()
		self.assertEqual(
			[(c[1], c[2]) for c in self._steps("punches")], [CHUNKS[0], ("2026-09-01", "2026-09-03")]
		)

	def test_the_parity_report_is_read_before_the_punches_are_copied(self):
		eg.run_endgame()
		names = [c[0] for c in self.calls]
		self.assertLess(names.index("parity"), names.index("punches"))

	def test_a_finished_run_marks_itself_done_and_agrees_with_the_nightly_pass(self):
		# The nightly (attendance_auto_recovery) re-runs the whole window while no
		# finished one-time run is on record. The endgame does strictly more, so
		# when it finishes it leaves the nightly's mark too — they must not fight.
		eg.run_endgame()
		self.assertTrue(self.defaults.get(eg.DONE_MARK))
		self.assertEqual(self.defaults.get(eg.auto.ONCE_MARK), TODAY)

	def test_a_second_call_after_a_finished_run_does_no_work_again(self):
		eg.run_endgame()
		self.calls.clear()
		out = eg.run_endgame()
		self.assertEqual(self.calls, [])
		self.assertIn("already", (out.get("note") or "").lower())


class TestResume(_Case):
	def test_a_capped_pass_stops_and_the_next_one_carries_on(self):
		with patch.object(eg, "MAX_CHUNKS_PER_PASS", 1):
			first = eg.run_endgame()
		self.assertTrue(first["more"])
		self.assertEqual([c[0] for c in self.calls if c[0] != "parity"], ["relabel"])
		run = first["run"]

		self.calls.clear()
		with patch.object(eg, "MAX_CHUNKS_PER_PASS", 1):
			second = eg.run_endgame()
		self.assertEqual(second["run"], run, "a resumed pass keeps the run id")
		self.assertEqual([c[0] for c in self.calls if c[0] != "parity"], ["relabel"])
		self.assertEqual(self._steps("relabel")[0][1], "2026-09-01", "it carries on at the next chunk")

	def test_a_killed_worker_leaves_a_marker_on_the_chunk_it_never_finished(self):
		# A kill gives no chance to tidy up, so the marker is written BEFORE the
		# work: the next pass redoes that one chunk, and every step is idempotent.
		self.raises["relabel"] = SystemExit("worker killed")
		with self.assertRaises(SystemExit):
			eg.run_endgame()
		state = json.loads(self.defaults[eg.STATE_MARK])
		self.assertEqual(state["step"], "relabel")
		self.assertEqual(state["cursor"], "2026-08-01")

	def test_the_resumed_pass_starts_at_the_marker_not_at_the_floor(self):
		self.defaults[eg.STATE_MARK] = json.dumps(
			{"run": "ENDGAME-TEST", "step": "recovery", "cursor": "2026-09-01", "counts": {}}
		)
		eg.run_endgame()
		self.assertEqual([c[0] for c in self.calls if c[0] != "parity"], ["recovery", "ot", "ot"])
		self.assertEqual(self._steps("recovery")[0][1], "2026-09-01")

	def test_a_finished_run_clears_its_marker(self):
		eg.run_endgame()
		self.assertIsNone(self.defaults.get(eg.STATE_MARK))


class TestStopSwitch(_Case):
	def test_the_stop_switch_halts_the_run_between_steps(self):
		calls = {"n": 0}

		def relabel(start, end, **kwargs):
			calls["n"] += 1
			return {"ok": True, "changed": [], "counts": {}}

		# Off for the first step, thrown after it: the run stops before the next.
		settings = [{}, {eg.STOP_SWITCH: 1}]

		def get_single(doctype):
			values = settings[min(calls["n"], len(settings) - 1)]
			return SimpleNamespace(get=lambda key, default=None: values.get(key, default))

		with (
			patch.object(eg.own, "relabel_system_rows", self._recorder("relabel", relabel)),
			patch.object(frappe, "get_single", get_single, create=True),
		):
			out = eg.run_endgame()
		self.assertTrue(out["stopped"])
		self.assertEqual([c[0] for c in self.calls if c[0] != "parity"], ["relabel"])
		self.assertIn(eg.STATE_MARK, self.defaults, "a halted run can be resumed")
		self.assertFalse(self.defaults.get(eg.DONE_MARK))

	def test_an_absent_stop_switch_means_run(self):
		with patch.object(frappe, "get_single", _settings({}), create=True):
			self.assertFalse(eg.stopped())

	def test_the_stop_switch_is_read_as_a_stop_only_when_it_is_ticked(self):
		with patch.object(frappe, "get_single", _settings({eg.STOP_SWITCH: 1}), create=True):
			self.assertTrue(eg.stopped())
		with patch.object(frappe, "get_single", _settings({eg.STOP_SWITCH: 0}), create=True):
			self.assertFalse(eg.stopped())


class TestSummary(_Case):
	def test_one_summary_for_the_whole_run_however_many_chunks(self):
		eg.run_endgame()
		self.assertEqual(self.notify.call_count, 1)

	def test_a_resumed_run_still_reports_exactly_once(self):
		with patch.object(eg, "MAX_CHUNKS_PER_PASS", 1):
			for _ in range(12):
				out = eg.run_endgame()
				if not out.get("more"):
					break
		self.assertEqual(self.notify.call_count, 1)

	def test_the_summary_is_not_written_twice_for_one_run_id(self):
		eg.run_endgame()
		self.defaults.pop(eg.DONE_MARK, None)
		self.calls.clear()
		eg.run_endgame()
		self.assertEqual(self.notify.call_count, 2, "a NEW run reports again")
		self.assertNotEqual(self.notify.call_args_list[0], self.notify.call_args_list[1])

	def test_the_summary_says_what_happened_in_plain_english(self):
		eg.run_endgame()
		body = self.notify.call_args.args[1]
		for phrase in (
			"relabelled",
			"copied from the old system",
			"rebuilt",
			"left alone on purpose",
			"need HR",
		):
			self.assertIn(phrase, body)

	def test_the_summary_carries_the_run_id_and_how_to_undo_it(self):
		out = eg.run_endgame()
		body = self.notify.call_args.args[1]
		self.assertIn(out["run"], body)
		self.assertIn("undo", body.lower())

	def test_the_counts_add_up_over_every_chunk(self):
		out = eg.run_endgame()
		counts = out["counts"]
		self.assertEqual(counts["relabelled"], 2)  # one row per chunk
		self.assertEqual(counts["punches_copied"], 2)
		self.assertEqual(counts["needs_hr"], 2)
		self.assertEqual(counts["left_alone"], 6)

	def test_the_summary_also_lands_on_the_error_log_trail(self):
		out = eg.run_endgame()
		self.assertTrue(any(out["run"] in (title or "") for title, _m in self.logged))


class TestRunId(_Case):
	def test_every_step_runs_under_the_same_run_id(self):
		seen = set()

		def relabel(start, end, **kwargs):
			seen.add(eg.current_run())
			return {"ok": True, "changed": [], "counts": {}}

		def recovery(start, end, **kwargs):
			seen.add(eg.current_run())
			return self._recovery(start, end)

		with (
			patch.object(eg.own, "relabel_system_rows", self._recorder("relabel", relabel)),
			patch.object(eg.auto, "_run", self._recorder("recovery", recovery)),
		):
			out = eg.run_endgame()
		self.assertEqual(seen, {out["run"]})

	def test_there_is_no_run_id_outside_a_run(self):
		self.assertIsNone(eg.current_run())
		eg.run_endgame()
		self.assertIsNone(eg.current_run(), "the run id is cleared when the pass ends")

	def test_a_crash_still_clears_the_run_id(self):
		self.raises["relabel"] = SystemExit("killed")
		with self.assertRaises(SystemExit):
			eg.run_endgame()
		self.assertIsNone(eg.current_run())

	def test_the_day_fix_log_stamps_the_run_id_on_every_entry(self):
		# The one filter that makes "undo the whole run" possible.
		from hrms.utils import attendance_recovery as rec

		written = {}

		def get_doc(payload):
			written.update(payload)
			return SimpleNamespace(
				name="HRFIX-1", flags=SimpleNamespace(ignore_permissions=False), insert=lambda: None
			)

		def relabel(start, end, **kwargs):
			with patch.object(frappe, "get_doc", get_doc):
				self.db.exists.return_value = True
				rec.log_day_fix("E1", "2026-08-10", "rebuild", source="recovery")
			return {"ok": True, "changed": [], "counts": {}}

		with patch.object(eg.own, "relabel_system_rows", self._recorder("relabel", relabel)):
			out = eg.run_endgame()
		self.assertEqual(written["run"], out["run"])

	def test_an_entry_written_outside_a_run_carries_no_run_id(self):
		from hrms.utils import attendance_recovery as rec

		written = {}

		def get_doc(payload):
			written.update(payload)
			return SimpleNamespace(
				name="HRFIX-2", flags=SimpleNamespace(ignore_permissions=False), insert=lambda: None
			)

		self.db.exists.return_value = True
		with patch.object(frappe, "get_doc", get_doc):
			rec.log_day_fix("E1", "2026-08-10", "rebuild", source="hr_fix_day")
		self.assertIsNone(written["run"])


class TestNeverRaises(_Case):
	def test_no_step_raises_into_the_scheduler(self):
		for step in ("relabel", "parity", "punches", "recovery", "ot"):
			with self.subTest(step=step):
				self.calls.clear()
				self.defaults.clear()
				self.notify.reset_mock()
				self.raises = {step: RuntimeError(f"{step} exploded")}
				out = eg.run_endgame()
				self.assertIsInstance(out, dict)
				self.assertTrue(any(step in str(note) for note in out["errors"]))

	def test_a_broken_step_does_not_stop_the_ones_after_it(self):
		self.raises = {"relabel": RuntimeError("boom")}
		eg.run_endgame()
		self.assertIn("recovery", [c[0] for c in self.calls])

	def test_a_broken_step_still_reaches_the_summary(self):
		self.raises = {"punches": RuntimeError("the ERP is down")}
		eg.run_endgame()
		self.notify.assert_called_once()
		self.assertIn("the ERP is down", self.notify.call_args.args[1])


class TestUndoRun(_Case):
	RUN = "ENDGAME-2026-09-16-01"

	def _entry(self, name, employee="E1", day="2026-08-10", undone=0, run=None, action="rebuild"):
		return frappe._dict(
			{
				"name": name,
				"run": run or self.RUN,
				"employee": employee,
				"fix_date": day,
				"action": action,
				"undone": undone,
				"before_state": json.dumps(
					{
						"name": "HR-ATT-1",
						"status": "Absent",
						"working_hours": 0,
						"in_time": None,
						"out_time": None,
					}
				),
				"after_state": json.dumps({"name": "HR-ATT-1", "status": "Present", "working_hours": 8}),
			}
		)

	def _undo(self, entries, protection=None):
		self.inserted = []

		def get_doc(payload):
			self.inserted.append(payload)
			return SimpleNamespace(
				name=f"HRFIX-U{len(self.inserted)}",
				flags=SimpleNamespace(ignore_permissions=False),
				insert=lambda: None,
			)

		with (
			patch.object(frappe, "get_all", MagicMock(return_value=entries)) as get_all,
			patch.object(frappe, "get_doc", get_doc),
			patch.object(eg.rec, "_day_protection", lambda e, d, u: (protection or {}).get(str(d))),
			patch.object(eg.rec, "_lock_employee", MagicMock()),
		):
			self.db.exists.return_value = True
			out = eg.undo_run(self.RUN)
		self.get_all = get_all
		return out

	def test_it_only_ever_reads_its_own_run(self):
		self._undo([self._entry("HRFIX-1")])
		self.assertEqual(self.get_all.call_args.kwargs["filters"]["run"], self.RUN)

	def test_an_entry_from_another_run_is_never_touched(self):
		out = self._undo([self._entry("HRFIX-9", run="ENDGAME-OTHER")])
		self.assertEqual(out["restored"], [])
		self.assertIn("another run", out["refused"][0]["reason"])

	def test_it_restores_the_day_exactly_as_it_stood_before(self):
		out = self._undo([self._entry("HRFIX-1")])
		self.assertEqual([r["entry"] for r in out["restored"]], ["HRFIX-1"])
		self.db.set_value.assert_any_call(
			"Attendance",
			"HR-ATT-1",
			{"status": "Absent", "working_hours": 0, "in_time": None, "out_time": None},
			update_modified=False,
		)

	def test_it_works_newest_first(self):
		self._undo([self._entry("HRFIX-1")])
		self.assertIn("desc", self.get_all.call_args.kwargs["order_by"])

	def test_an_entry_already_undone_is_refused(self):
		out = self._undo([self._entry("HRFIX-1", undone=1)])
		self.assertEqual(out["restored"], [])
		self.assertIn("already undone", out["refused"][0]["reason"])

	def test_a_day_that_has_since_been_paid_or_approved_is_refused_and_said_so(self):
		out = self._undo(
			[self._entry("HRFIX-1", day="2026-08-10"), self._entry("HRFIX-2", day="2026-08-11")],
			protection={"2026-08-10": "a payout depends on this day (SAL-1)"},
		)
		self.assertEqual([r["entry"] for r in out["restored"]], ["HRFIX-2"])
		refused = out["refused"][0]
		self.assertEqual(refused["date"], "2026-08-10")
		self.assertIn("payout", refused["reason"])

	def test_a_day_hr_has_edited_since_is_refused(self):
		out = self._undo([self._entry("HRFIX-1")], protection={"2026-08-10": "was marked by HR by hand"})
		self.assertEqual(out["restored"], [])
		self.assertIn("HR", out["refused"][0]["reason"])

	def test_it_marks_the_entry_undone_so_a_second_undo_is_a_no_op(self):
		self._undo([self._entry("HRFIX-1")])
		marked = [c for c in self.db.set_value.call_args_list if c.args[0] == eg.rec.DAY_FIX_LOG]
		self.assertTrue(marked, "the original entry is stamped undone")
		self.assertEqual(marked[0].args[2]["undone"], 1)

	def test_it_writes_its_own_entry_pointing_at_the_one_it_reversed(self):
		self._undo([self._entry("HRFIX-1")])
		self.assertEqual(self.inserted[0]["action"], "undo_run")
		self.assertEqual(self.inserted[0]["undo_of"], "HRFIX-1")

	def test_a_rolled_back_rebuild_has_nothing_to_reverse(self):
		out = self._undo([self._entry("HRFIX-1", action="rebuild-rolled-back")])
		self.assertEqual(out["restored"], [])
		self.assertIn("nothing", out["refused"][0]["reason"].lower())

	def test_it_never_raises(self):
		with patch.object(frappe, "get_all", MagicMock(side_effect=RuntimeError("db gone"))):
			out = eg.undo_run(self.RUN)
		self.assertEqual(out["restored"], [])
		self.assertIn("db gone", str(out.get("note")))


class TestMarkersDoNotFight(_Case):
	def test_the_nightly_stands_aside_while_an_endgame_run_is_unfinished(self):
		self.defaults[eg.STATE_MARK] = json.dumps(
			{"run": "ENDGAME-X", "step": "recovery", "cursor": "2026-09-01", "counts": {}}
		)
		with (
			patch.object(eg.auto, "is_job_enqueued", return_value=False),
			patch.object(eg.auto, "_run", MagicMock()) as inner,
		):
			self.assertIsNone(eg.auto.run_nightly())
		inner.assert_not_called()

	def test_the_nightly_runs_its_own_week_once_the_endgame_has_finished(self):
		eg.run_endgame()
		with (
			patch.object(eg.auto, "is_job_enqueued", return_value=False),
			patch.object(eg.auto, "nowdate", lambda: TODAY),
			patch.object(eg.auto, "_safe", MagicMock(return_value={})) as safe,
		):
			eg.auto.run_nightly()
		safe.assert_called_once()


if __name__ == "__main__":
	unittest.main(verbosity=2)

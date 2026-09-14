"""`hrms.sync.missing_checkins` — which source punches never reached the hub.

After cutover the pull no longer carries Employee Checkin, so a punch recorded
on the source ERP after the last pull is simply absent here, and nothing says
so. Names cannot identify a punch across the two sites (independent
`EMP-CKIN-.MM.-.YYYY.-.######` counters), so the report matches on the natural
key (employee, time to the second, log_type).

Bench-free: `frappe` is stubbed. Run it as a FILE:

    PYTHONPATH=. python hrms/sync/test_missing_checkins.py
"""

import datetime
import importlib.util
import pathlib
import sys
import types
import unittest

SOURCE = pathlib.Path(__file__).resolve().parent / "missing_checkins.py"
D = datetime.datetime


def _load():
	"""Load the module from its path with a minimal `frappe` stand-in."""
	fake = types.ModuleType("frappe")
	fake.whitelist = lambda *a, **k: lambda fn: fn
	fake._ = lambda text: text
	sys.modules.setdefault("frappe", fake)
	spec = importlib.util.spec_from_file_location("missing_checkins_under_test", SOURCE)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


mc = _load()


def punch(employee, time, log_type, name="R-1", **extra):
	return {"employee": employee, "time": time, "log_type": log_type, "name": name, **extra}


class DiffPunches(unittest.TestCase):
	def test_exact_match_is_not_missing(self):
		out = mc.diff_punches(
			[punch("EMP-1", "2026-09-03 08:48:00", "IN")],
			[punch("EMP-1", D(2026, 9, 3, 8, 48), "IN", name="L-9")],
		)
		self.assertEqual(out["missing"], [])
		self.assertEqual(out["type_mismatch"], [])
		self.assertEqual(out["matched"], 1)

	def test_punch_absent_locally_is_missing(self):
		out = mc.diff_punches(
			[
				punch("EMP-1", "2026-09-03 08:48:00", "IN", name="R-1"),
				punch("EMP-1", "2026-09-04 01:04:00", "OUT", name="R-2"),
			],
			[punch("EMP-1", D(2026, 9, 3, 8, 48), "IN")],
		)
		self.assertEqual([row["remote_name"] for row in out["missing"]], ["R-2"])
		self.assertEqual(out["missing"][0]["time"], D(2026, 9, 4, 1, 4))
		self.assertEqual(out["missing"][0]["log_type"], "OUT")

	def test_same_moment_other_log_type_is_a_type_mismatch_not_missing(self):
		out = mc.diff_punches(
			[punch("EMP-1", "2026-09-09 23:23:00", "OUT", name="R-7")],
			[punch("EMP-1", D(2026, 9, 9, 23, 23), "IN", name="L-3")],
		)
		self.assertEqual(out["missing"], [])
		self.assertEqual(len(out["type_mismatch"]), 1)
		row = out["type_mismatch"][0]
		self.assertEqual((row["log_type"], row["local_log_type"]), ("OUT", "IN"))
		self.assertEqual((row["remote_name"], row["local_name"]), ("R-7", "L-3"))

	def test_exact_match_wins_over_a_type_mismatch_at_the_same_moment(self):
		# ERP holds IN and OUT at the same second; the hub holds only the OUT.
		out = mc.diff_punches(
			[
				punch("EMP-1", "2026-09-09 12:00:00", "IN", name="R-1"),
				punch("EMP-1", "2026-09-09 12:00:00", "OUT", name="R-2"),
			],
			[punch("EMP-1", D(2026, 9, 9, 12, 0), "OUT")],
		)
		self.assertEqual(out["matched"], 1)
		self.assertEqual([row["remote_name"] for row in out["missing"]], ["R-1"])
		self.assertEqual(out["type_mismatch"], [])

	def test_microseconds_are_truncated_on_both_sides(self):
		out = mc.diff_punches(
			[punch("EMP-1", "2026-09-03 08:48:12.734000", "IN")],
			[punch("EMP-1", D(2026, 9, 3, 8, 48, 12, 1), "IN")],
		)
		self.assertEqual(out["missing"], [])
		self.assertEqual(out["matched"], 1)

	def test_a_different_second_is_a_different_punch(self):
		out = mc.diff_punches(
			[punch("EMP-1", "2026-09-03 08:48:13", "IN")],
			[punch("EMP-1", D(2026, 9, 3, 8, 48, 12), "IN")],
		)
		self.assertEqual(len(out["missing"]), 1)

	def test_string_and_datetime_and_iso_t_forms_compare_equal(self):
		out = mc.diff_punches(
			[
				punch("EMP-1", D(2026, 9, 3, 8, 48), "IN", name="R-1"),
				punch("EMP-2", "2026-09-03T09:00:00", "IN", name="R-2"),
			],
			[
				punch("EMP-1", "2026-09-03 08:48:00", "IN"),
				punch("EMP-2", D(2026, 9, 3, 9, 0), "IN"),
			],
		)
		self.assertEqual(out["missing"], [])
		self.assertEqual(out["matched"], 2)

	def test_duplicate_remote_punches_need_as_many_local_ones(self):
		out = mc.diff_punches(
			[
				punch("EMP-1", "2026-09-03 08:48:00", "IN", name="R-1"),
				punch("EMP-1", "2026-09-03 08:48:00", "IN", name="R-2"),
			],
			[punch("EMP-1", D(2026, 9, 3, 8, 48), "IN")],
		)
		self.assertEqual(out["matched"], 1)
		self.assertEqual(len(out["missing"]), 1)

	def test_other_employee_at_the_same_moment_does_not_match(self):
		out = mc.diff_punches(
			[punch("EMP-1", "2026-09-03 08:48:00", "IN")],
			[punch("EMP-2", D(2026, 9, 3, 8, 48), "IN")],
		)
		self.assertEqual(len(out["missing"]), 1)

	def test_past_midnight_flags_only_an_out_before_six(self):
		out = mc.diff_punches(
			[
				punch("EMP-1", "2026-09-04 01:04:00", "OUT", name="late-out"),
				punch("EMP-1", "2026-09-04 05:59:59", "OUT", name="edge-out"),
				punch("EMP-1", "2026-09-04 06:00:00", "OUT", name="six-out"),
				punch("EMP-1", "2026-09-04 02:00:00", "IN", name="night-in"),
				punch("EMP-1", "2026-09-09 23:23:00", "OUT", name="evening-out"),
			],
			[],
		)
		flags = {row["remote_name"]: row["past_midnight"] for row in out["missing"]}
		self.assertEqual(
			flags,
			{
				"late-out": True,
				"edge-out": True,
				"six-out": False,
				"night-in": False,
				"evening-out": False,
			},
		)

	def test_empty_inputs(self):
		self.assertEqual(
			mc.diff_punches([], []),
			{"matched": 0, "missing": [], "type_mismatch": []},
		)
		out = mc.diff_punches([], [punch("EMP-1", D(2026, 9, 3, 8, 48), "IN")])
		self.assertEqual((out["matched"], out["missing"]), (0, []))

	def test_missing_rows_come_back_in_employee_then_time_order(self):
		out = mc.diff_punches(
			[
				punch("EMP-2", "2026-09-03 08:00:00", "IN", name="c"),
				punch("EMP-1", "2026-09-04 08:00:00", "IN", name="b"),
				punch("EMP-1", "2026-09-03 08:00:00", "IN", name="a"),
			],
			[],
		)
		self.assertEqual([row["remote_name"] for row in out["missing"]], ["a", "b", "c"])


class ResolveWindow(unittest.TestCase):
	TODAY = datetime.date(2026, 9, 14)

	def test_default_is_the_last_fourteen_days_including_today(self):
		self.assertEqual(
			mc.resolve_window(None, None, self.TODAY),
			(datetime.date(2026, 9, 1), datetime.date(2026, 9, 14)),
		)

	def test_explicit_strings_are_parsed(self):
		self.assertEqual(
			mc.resolve_window("2026-09-03", "2026-09-09", self.TODAY),
			(datetime.date(2026, 9, 3), datetime.date(2026, 9, 9)),
		)

	def test_only_from_date_runs_to_today(self):
		self.assertEqual(
			mc.resolve_window("2026-09-10", None, self.TODAY),
			(datetime.date(2026, 9, 10), self.TODAY),
		)

	def test_a_window_over_the_cap_is_refused_not_clipped(self):
		with self.assertRaises(ValueError):
			mc.resolve_window("2026-01-01", "2026-09-14", self.TODAY)

	def test_exactly_the_cap_is_allowed(self):
		start = self.TODAY - datetime.timedelta(days=mc.MAX_WINDOW_DAYS - 1)
		self.assertEqual(mc.resolve_window(start, self.TODAY, self.TODAY), (start, self.TODAY))

	def test_reversed_window_is_refused(self):
		with self.assertRaises(ValueError):
			mc.resolve_window("2026-09-10", "2026-09-01", self.TODAY)


class BuildReport(unittest.TestCase):
	WINDOW = (datetime.date(2026, 9, 1), datetime.date(2026, 9, 14))

	def build(self, remote, local, employees, sample=50):
		return mc.build_report("Nasty-Live", self.WINDOW, remote, local, employees, sample=sample)

	def test_unmapped_remote_employees_are_listed_not_silently_dropped(self):
		out = self.build(
			[
				punch("EMP-1", "2026-09-03 08:48:00", "IN", name="R-1"),
				punch("EMP-GHOST", "2026-09-03 08:00:00", "IN", name="R-2"),
				punch("EMP-GHOST", "2026-09-03 17:00:00", "OUT", name="R-3"),
			],
			[],
			{"EMP-1": "Aisha"},
		)
		self.assertEqual(out["unmapped_employees"], [{"employee": "EMP-GHOST", "remote_punches": 2}])
		self.assertEqual(out["missing"], 1)
		self.assertEqual(out["remote_rows"], 3)
		self.assertEqual(out["by_employee"], {"EMP-1": 1})

	def test_report_shape_and_sample(self):
		out = self.build(
			[
				punch("EMP-1", "2026-09-03 08:48:00", "IN", name="R-1", device_id="gate"),
				punch("EMP-1", "2026-09-04 01:04:00", "OUT", name="R-2"),
				punch("EMP-1", "2026-09-09 23:23:00", "OUT", name="R-3"),
			],
			[punch("EMP-1", D(2026, 9, 9, 23, 23), "IN", name="L-1")],
			{"EMP-1": "Aisha"},
		)
		self.assertEqual(out["instance"], "Nasty-Live")
		self.assertEqual(out["window"], {"from_date": "2026-09-01", "to_date": "2026-09-14"})
		self.assertEqual((out["remote_rows"], out["local_rows"]), (3, 1))
		self.assertEqual((out["missing"], out["type_mismatch"]), (2, 1))
		self.assertEqual(
			out["sample"][0],
			{
				"employee": "EMP-1",
				"employee_name": "Aisha",
				"time": "2026-09-03 08:48:00",
				"log_type": "IN",
				"remote_name": "R-1",
				"device_id": "gate",
				"past_midnight": False,
			},
		)
		self.assertTrue(out["sample"][1]["past_midnight"])
		self.assertEqual(out["type_mismatch_sample"][0]["local_log_type"], "IN")

	def test_sample_is_capped_but_counts_are_not(self):
		remote = [punch("EMP-1", f"2026-09-03 08:{m:02d}:00", "IN", name=f"R-{m}") for m in range(10)]
		out = self.build(remote, [], {"EMP-1": "Aisha"}, sample=3)
		self.assertEqual(out["missing"], 10)
		self.assertEqual(len(out["sample"]), 3)


class RemoteRead(unittest.TestCase):
	"""The remote read filters on the punch TIME, never on `modified`, and only reads."""

	class FakeClient:
		instance_name = "Nasty-Live"

		def __init__(self, pages):
			self.pages = pages
			self.calls = []

		def get_list(self, doctype, filters=None, fields=None, limit=None, start=0, order_by=None):
			self.calls.append({"doctype": doctype, "filters": filters, "fields": fields, "limit": limit})
			return self.pages.get(doctype, [])

	def split_none(self, filters):
		yield filters

	def test_filters_by_time_window_and_employee_scope(self):
		client = self.FakeClient({"Employee Checkin": [punch("EMP-1", "2026-09-03 08:48:00", "IN")]})
		rows = mc.fetch_remote_punches(
			client,
			(datetime.date(2026, 9, 1), datetime.date(2026, 9, 14)),
			employees=["EMP-1"],
			split=self.split_none,
		)
		self.assertEqual(len(rows), 1)
		call = client.calls[0]
		self.assertEqual(call["doctype"], "Employee Checkin")
		self.assertEqual(call["filters"]["time"], ["between", ["2026-09-01", "2026-09-14"]])
		self.assertNotIn("modified", call["filters"])
		self.assertEqual(call["filters"]["employee"], ["in", ["EMP-1"]])
		self.assertEqual(set(call["fields"]), {"name", "employee", "time", "log_type", "device_id"})
		self.assertIsNone(call["limit"])

	def test_no_scope_reads_the_whole_window(self):
		client = self.FakeClient({})
		mc.fetch_remote_punches(
			client, (datetime.date(2026, 9, 1), datetime.date(2026, 9, 2)), None, split=self.split_none
		)
		self.assertNotIn("employee", client.calls[0]["filters"])

	def test_an_empty_scope_reads_nothing(self):
		client = self.FakeClient({})
		rows = mc.fetch_remote_punches(
			client, (datetime.date(2026, 9, 1), datetime.date(2026, 9, 2)), [], split=self.split_none
		)
		self.assertEqual((rows, client.calls), ([], []))


if __name__ == "__main__":
	unittest.main()

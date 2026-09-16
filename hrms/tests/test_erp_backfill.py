"""The old ERP's punches, compared with this hub's — read-only (B1, 16 Sep 2026).

Before cutover (4 September 2026) staff punched on the source ERP as well as
here, and the mirror never carried those punches. Days therefore read Half Day
or Absent on the hub although the ERP holds the missing tap. Nothing said so
per employee-day, so nobody could tell a real absence from a missing copy.

This report says it: for every employee-day in the window, the ERP's punches,
the hub's punches, what the hub day currently reads, and a verdict. It writes
NOTHING — not here, and never on the ERP.

A tap within 3 minutes of another counts as the SAME tap, the tolerance the
copy itself refuses duplicates on, so the report predicts what a copy would do.

    PYTHONPATH=. python3 hrms/tests/test_erp_backfill.py
"""

import pathlib
import sys
import unittest
from datetime import date, datetime
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

from hrms.sync import erp_backfill as bf

EMP = "HR-EMP-00313"
DAY = date(2026, 8, 17)
D = datetime


def _erp(moment, log_type="IN", name="ERP-1"):
	return {"name": name, "employee": EMP, "time": moment, "log_type": log_type, "device_id": "ERP"}


def _hub(moment, log_type="IN", name="EC-1", **extra):
	row = {
		"name": name,
		"employee": EMP,
		"time": moment,
		"log_type": log_type,
		"shift_start": D(2026, 8, 17, 0, 0),
		"skip_auto_attendance": 0,
		"remote_approval_status": None,
	}
	row.update(extra)
	return row


class TestMatchPunches(unittest.TestCase):
	"""One-to-one matching with the copy's own 3-minute tolerance."""

	def test_the_same_second_matches(self):
		out = bf.match_punches([D(2026, 8, 17, 9, 0)], [D(2026, 8, 17, 9, 0)])
		self.assertEqual((len(out["matched"]), out["missing"], out["extra"]), (1, [], []))

	def test_a_tap_two_minutes_apart_is_the_same_tap(self):
		out = bf.match_punches([D(2026, 8, 17, 9, 0)], [D(2026, 8, 17, 9, 2)])
		self.assertEqual(out["missing"], [])

	def test_a_tap_four_minutes_apart_is_a_different_tap(self):
		out = bf.match_punches([D(2026, 8, 17, 9, 0)], [D(2026, 8, 17, 9, 4)])
		self.assertEqual(out["missing"], [D(2026, 8, 17, 9, 0)])
		self.assertEqual(out["extra"], [D(2026, 8, 17, 9, 4)])

	def test_an_erp_punch_with_no_hub_tap_is_missing(self):
		out = bf.match_punches([D(2026, 8, 17, 9, 0), D(2026, 8, 17, 18, 0)], [D(2026, 8, 17, 9, 0)])
		self.assertEqual(out["missing"], [D(2026, 8, 17, 18, 0)])

	def test_a_hub_tap_with_no_erp_punch_is_extra(self):
		out = bf.match_punches([D(2026, 8, 17, 9, 0)], [D(2026, 8, 17, 9, 0), D(2026, 8, 17, 18, 0)])
		self.assertEqual(out["extra"], [D(2026, 8, 17, 18, 0)])

	def test_two_erp_punches_need_two_hub_taps(self):
		"""One hub tap cannot stand for both — matching is one-to-one."""
		out = bf.match_punches([D(2026, 8, 17, 9, 0), D(2026, 8, 17, 9, 1)], [D(2026, 8, 17, 9, 0)])
		self.assertEqual(len(out["matched"]), 1)
		self.assertEqual(out["missing"], [D(2026, 8, 17, 9, 1)])


class TestDayVerdict(unittest.TestCase):
	def test_every_punch_on_both_sides_matches(self):
		self.assertEqual(bf.day_verdict({"matched": [1, 2], "missing": [], "extra": []}, row=True), "matches")

	def test_missing_punches_are_counted(self):
		self.assertEqual(
			bf.day_verdict({"matched": [1], "missing": [2], "extra": []}, row=True), "hub missing 1"
		)

	def test_extra_punches_are_counted(self):
		self.assertEqual(
			bf.day_verdict({"matched": [1], "missing": [], "extra": [2, 3]}, row=True), "hub extra 2"
		)

	def test_missing_and_extra_are_both_named(self):
		self.assertEqual(
			bf.day_verdict({"matched": [], "missing": [1], "extra": [2]}, row=True),
			"hub missing 1, hub extra 1",
		)

	def test_a_day_with_no_hub_row_says_so(self):
		self.assertEqual(bf.day_verdict({"matched": [1], "missing": [], "extra": []}, row=None), "no hub row")


class TestParityRows(unittest.TestCase):
	"""One line per employee-day: both sides' punches, the hub day, the verdict."""

	def setUp(self):
		self.erp = [_erp(D(2026, 8, 17, 9, 0)), _erp(D(2026, 8, 17, 18, 0), "OUT", "ERP-2")]
		self.hub = [_hub(D(2026, 8, 17, 9, 0))]
		self.rows = {(EMP, DAY): {"name": "HR-ATT-1", "status": "Half Day", "working_hours": 0.0}}

	def test_the_line_carries_both_sides_and_the_verdict(self):
		lines = bf.parity_rows(EMP, self.erp, self.hub, self.rows, DAY, DAY)
		self.assertEqual(len(lines), 1)
		line = lines[0]
		self.assertEqual((line["employee"], line["date"]), (EMP, str(DAY)))
		self.assertEqual((line["erp_punches"], line["hub_punches"]), (2, 1))
		self.assertEqual(line["erp_times"], ["2026-08-17 09:00:00", "2026-08-17 18:00:00"])
		self.assertEqual(line["hub_times"], ["2026-08-17 09:00:00"])
		self.assertEqual(line["missing_on_hub"], ["2026-08-17 18:00:00"])
		self.assertEqual((line["status"], line["working_hours"]), ("Half Day", 0.0))
		self.assertEqual(line["verdict"], "hub missing 1")

	def test_a_day_outside_the_window_is_not_reported(self):
		self.assertEqual(bf.parity_rows(EMP, self.erp, self.hub, self.rows, date(2026, 8, 18), DAY), [])

	def test_a_day_the_hub_alone_holds_is_still_a_line(self):
		lines = bf.parity_rows(EMP, [], self.hub, self.rows, DAY, DAY)
		self.assertEqual((lines[0]["erp_punches"], lines[0]["verdict"]), (0, "hub extra 1"))

	def test_an_out_after_midnight_belongs_to_the_shift_day_before(self):
		lines = bf.parity_rows(EMP, [_erp(D(2026, 8, 18, 1, 4), "OUT")], [], {}, DAY, DAY)
		self.assertEqual(lines[0]["date"], str(DAY))
		self.assertEqual(lines[0]["verdict"], "hub missing 1, no hub row")


class TestParityReads(unittest.TestCase):
	"""The report pages the ERP per employee and writes nothing on either side."""

	def setUp(self):
		self.client = MagicMock()
		self.client.get_list.return_value = [_erp(D(2026, 8, 17, 18, 0), "OUT")]
		self.db = MagicMock()
		patches = [
			patch.object(frappe, "db", self.db),
			patch.object(bf, "_client", return_value=self.client),
			patch.object(bf, "_source_instance", return_value="erp-live"),
			patch.object(bf, "_employees_in_scope", return_value=[EMP]),
			patch.object(bf, "_hub_punches", return_value={EMP: [_hub(D(2026, 8, 17, 9, 0))]}),
			patch.object(bf, "_attendance_rows", return_value={}),
			patch.object(frappe, "get_all", MagicMock(return_value=[])),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)

	def test_it_reads_the_erp_once_per_employee_and_reports_the_gap(self):
		out = bf.parity(DAY, DAY)
		self.assertEqual(self.client.get_list.call_count, 1)
		# The ERP holds the 18:00 OUT this hub never got; the hub's 09:00 IN was
		# made here after the mirror stopped, so the ERP does not hold it either.
		self.assertEqual(out["rows"][0]["verdict"], "hub missing 1, hub extra 1, no hub row")
		self.assertEqual(out["counts"]["hub_missing_punches"], 1)
		self.assertEqual(out["counts"]["hub_extra_punches"], 1)

	def test_it_never_writes(self):
		bf.parity(DAY, DAY)
		self.db.sql.assert_not_called()
		self.db.set_value.assert_not_called()
		self.db.commit.assert_not_called()
		self.assertEqual(
			[c for c in self.client.method_calls if c[0] not in ("get_list", "get_doc")],
			[],
			"the report may only GET from the ERP",
		)

	def test_the_write_switch_does_not_gate_a_report(self):
		"""Reports are always allowed; only the copy asks the switch."""
		with patch.object(bf, "_enabled", return_value=False):
			self.assertEqual(len(bf.parity(DAY, DAY)["rows"]), 1)

	def test_a_window_after_the_cutover_is_refused(self):
		with self.assertRaises(ValueError):
			bf.parity(date(2026, 9, 4), date(2026, 9, 5))


class TestParityIsFenced(unittest.TestCase):
	"""The whitelisted read is HR Manager / System Manager and never company-fenced."""

	def test_it_asks_for_the_roles_and_refuses_a_fenced_caller(self):
		with (
			patch.object(frappe, "only_for", MagicMock(), create=True) as only_for,
			patch.object(bf, "parity", return_value={"rows": []}) as report,
			patch("hrms.overrides.company_scope.require_unfenced", MagicMock()) as unfenced,
		):
			bf.parity_report(str(DAY), str(DAY))
		only_for.assert_called_once_with(("System Manager", "HR Manager"))
		unfenced.assert_called_once()
		report.assert_called_once()


if __name__ == "__main__":
	unittest.main()

"""The "Forgot to check out?" banner reads a session the way attendance does.

Group 1 review W3 (14 Sep 2026): get_unresolved_stale_in paired punches by
log_type, so a day worker's 08:55 IN and her 18:31 tap stored as IN offered a
forgotten check-out for 18:31 — while the shift's "Alternating entries" rule
had already paired the two into a full day. A second repair then broke it.

The banner now uses the session rule the shift stamp uses
(hrms.utils.shift_resolution.session_is_open): within one shift group (same
shift and shift_start, not rejected, not skip-stamped) an even-numbered punch
closes the session, and a later punch of the group closes the one before it.
Punches with no shift keep the log_type rule.

    PYTHONPATH=. python3 hrms/tests/test_stale_in_banner_session.py
"""

import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parents[2]), str(Path(__file__).resolve().parent)]
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.api import remote_checkin

NOW = datetime(2026, 9, 14, 10, 0)
DAY11 = ("9AM - 6PM", datetime(2026, 9, 11, 9))
DAY12 = ("9AM - 6PM", datetime(2026, 9, 12, 9))


def _row(name, time, log_type, stamp=None, **kw):
	shift, start = stamp or (None, None)
	row = frappe._dict(
		name=name,
		time=time,
		log_type=log_type,
		is_abandoned=0,
		remote_approval_status=None,
		skip_auto_attendance=0,
		shift=shift,
		shift_start=start,
	)
	row.update(kw)
	return row


def _banner(rows):
	newest_first = sorted(rows, key=lambda r: r.time, reverse=True)
	with (
		patch.object(frappe, "get_all", return_value=newest_first),
		patch.object(remote_checkin, "get_employee", return_value="HR-EMP-001"),
		patch.object(remote_checkin, "employee_now", return_value=NOW),
	):
		return remote_checkin.get_unresolved_stale_in()


class TestBannerFollowsTheShiftSession(unittest.TestCase):
	def test_a_mislabelled_second_in_is_the_check_out_and_offers_nothing(self):
		rows = [
			_row("CKIN-0855", datetime(2026, 9, 11, 8, 55), "IN", DAY11),
			_row("CKIN-1831", datetime(2026, 9, 11, 18, 31), "IN", DAY11),
		]
		self.assertEqual(_banner(rows), {})

	def test_a_real_forgotten_check_out_is_still_offered(self):
		rows = [
			_row("CKIN-0855", datetime(2026, 9, 11, 8, 55), "IN", DAY11),
			_row("CKIN-N0855", datetime(2026, 9, 12, 8, 55), "IN", DAY12),
			_row("CKIN-N1800", datetime(2026, 9, 12, 18), "OUT", DAY12),
		]
		self.assertEqual(_banner(rows).get("name"), "CKIN-0855")

	def test_back_from_lunch_without_a_final_check_out_is_offered(self):
		rows = [
			_row("CKIN-0900", datetime(2026, 9, 11, 9), "IN", DAY11),
			_row("CKIN-1300", datetime(2026, 9, 11, 13), "OUT", DAY11),
			_row("CKIN-1400", datetime(2026, 9, 11, 14), "IN", DAY11),
		]
		self.assertEqual(_banner(rows).get("name"), "CKIN-1400")

	def test_a_rejected_second_tap_does_not_close_the_session(self):
		rows = [
			_row("CKIN-0855", datetime(2026, 9, 11, 8, 55), "IN", DAY11),
			_row(
				"CKIN-1831",
				datetime(2026, 9, 11, 18, 31),
				"IN",
				DAY11,
				remote_approval_status="Rejected",
				skip_auto_attendance=1,
			),
		]
		self.assertEqual(_banner(rows).get("name"), "CKIN-0855")

	def test_punches_with_no_shift_keep_the_log_type_rule(self):
		rows = [_row("CKIN-A", datetime(2026, 9, 11, 8, 55), "IN")]
		self.assertEqual(_banner(rows).get("name"), "CKIN-A")

	def test_the_lookup_reads_the_shift_stamp(self):
		with (
			patch.object(frappe, "get_all", return_value=[]) as get_all,
			patch.object(remote_checkin, "get_employee", return_value="HR-EMP-001"),
			patch.object(remote_checkin, "employee_now", return_value=NOW),
		):
			remote_checkin.get_unresolved_stale_in()
		fields = get_all.call_args.kwargs["fields"]
		for field in ("shift", "shift_start", "skip_auto_attendance"):
			self.assertIn(field, fields)


if __name__ == "__main__":
	unittest.main()

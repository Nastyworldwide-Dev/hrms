"""The abandoned-IN sweeper must judge each IN against ITS OWN session.

_has_matching_close used to accept ANY later OUT as closing an IN, so the
buried-forgotten-checkout case — IN Mon (forgotten), IN Tue, OUT Tue — was
never tagged: Tuesday's OUT "closed" Monday's session and HR's abandoned-IN
alert stayed silent about the very row the PWA banner was surfacing. It also
counted REJECTED late-OUTs as closing, so one rejected resubmission suppressed
the tag forever.

This was the third divergent implementation of "does this IN have a closing
OUT" (the OT pairing engine and submit_late_checkout each had their own). The
sweeper now matches submit_late_checkout's rule: bounded by the next IN,
rejected OUTs excluded, NULL statuses probed separately (SQL three-valued
logic would silently drop legacy rows from a bare !=).

AST only — no bench required.
"""

import ast
import datetime
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path[:0] = [
	str(pathlib.Path(__file__).resolve().parents[2]),
	str(pathlib.Path(__file__).resolve().parent),
]
import _frappe_stub

_frappe_stub.install()

import frappe

SWEEPER = pathlib.Path(__file__).resolve().parent.parent / "utils" / "checkin_sweeper.py"


def _close_fn():
	for node in ast.walk(ast.parse(SWEEPER.read_text())):
		if isinstance(node, ast.FunctionDef) and node.name == "_has_matching_close":
			return node
	raise AssertionError("_has_matching_close not found")


class TestSweeperSessionBound(unittest.TestCase):
	def _constants(self):
		return {
			n.value for n in ast.walk(_close_fn()) if isinstance(n, ast.Constant) and isinstance(n.value, str)
		}

	def test_close_check_is_bounded_by_the_next_in(self):
		constants = self._constants()
		self.assertIn("between", constants, "the any-later-OUT check is back — buried INs go untagged")
		self.assertIn("IN", constants, "the next-IN session bound is gone")

	def test_rejected_outs_do_not_close_a_session(self):
		self.assertIn(
			"Rejected",
			self._constants(),
			"a rejected late-OUT closes the session again — one rejected "
			"resubmission would suppress the abandoned tag forever",
		)


class TestStaleLateCheckoutRequestsReachHr(unittest.TestCase):
	"""E18: a forgotten check-out request nobody decides left the day on Half
	Day for ever. After STALE_REQUEST_DAYS the 10:00 job tells HR, once per
	request, and never decides for them."""

	NOW = datetime.datetime(2026, 9, 14, 10, 0)

	def _run(self, requests, times=1):
		from hrms.overrides import remote_checkin_request_hooks as hooks
		from hrms.utils import checkin_sweeper as sweeper

		self.filters = []
		self.error_logs = []
		db = MagicMock()
		db.exists.side_effect = lambda doctype, filters=None, **kw: (
			doctype == "Error Log"
			and any(
				log["title"] == filters.get("method")
				and log["reference_name"] == filters.get("reference_name")
				for log in self.error_logs
			)
		)
		db.get_value.return_value = "NSTY"

		def get_all(doctype, filters=None, **kw):
			self.filters.append((doctype, dict(filters or {})))
			return list(requests) if doctype == "Remote Checkin Request" else []

		def log_error(title=None, message=None, reference_doctype=None, reference_name=None, **kw):
			self.error_logs.append({"title": title, "reference_name": reference_name})
			return frappe._dict(name=f"ERR-{len(self.error_logs)}")

		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_all", side_effect=get_all),
			patch.object(frappe, "get_doc") as get_doc,
			patch.object(frappe, "log_error", side_effect=log_error),
			patch.object(sweeper, "now_datetime", return_value=self.NOW),
			patch.object(hooks, "notify_hr") as notify_hr,
		):
			counts = [sweeper.escalate_stale_late_checkout_requests() for _ in range(times)]
		return counts, notify_hr, db, get_doc

	def _request(self, name="RCR-OLD"):
		return frappe._dict(
			name=name,
			employee="EMP-1",
			employee_name="Ria",
			checkin="OUT-1",
			checkin_time=datetime.datetime(2026, 9, 9, 21, 0),
			creation=datetime.datetime(2026, 9, 10, 8, 0),
		)

	def test_lists_only_pending_late_checkouts_older_than_the_limit(self):
		from hrms.utils import checkin_sweeper as sweeper

		self._run([self._request()])
		doctype, filters = self.filters[0]
		self.assertEqual(doctype, "Remote Checkin Request")
		self.assertEqual(filters["status"], "Pending")
		self.assertEqual(filters["is_late_checkout"], 1)
		self.assertEqual(
			filters["creation"], ["<=", self.NOW - datetime.timedelta(days=sweeper.STALE_REQUEST_DAYS)]
		)

	def test_hr_is_told_once_per_request_and_nothing_is_decided(self):
		counts, notify_hr, db, get_doc = self._run([self._request(), self._request("RCR-OLD-2")], times=2)
		self.assertEqual(counts, [2, 0], "the second run must find both already escalated")
		self.assertEqual(notify_hr.call_count, 2)
		self.assertEqual(sorted(call.args[3] for call in notify_hr.call_args_list), ["RCR-OLD", "RCR-OLD-2"])
		call = notify_hr.call_args_list[0]
		self.assertEqual(call.args[2], "Remote Checkin Request")
		self.assertIn("Ria", call.args[1])
		self.assertEqual(call.kwargs.get("company") or call.args[4], "NSTY")
		self.assertEqual([log["title"] for log in self.error_logs], [sweeper_title()] * 2)
		db.set_value.assert_not_called()
		get_doc.assert_not_called()

	def test_the_daily_job_runs_the_escalation(self):
		from hrms.utils import checkin_sweeper as sweeper

		with (
			patch.object(frappe, "get_all", return_value=[]),
			patch.object(frappe, "db", MagicMock()),
			patch.object(sweeper, "escalate_stale_late_checkout_requests") as escalate,
		):
			sweeper.sweep_stale_ins()
		escalate.assert_called_once()


def sweeper_title():
	from hrms.utils import checkin_sweeper as sweeper

	return sweeper.STALE_REQUEST_TITLE


if __name__ == "__main__":
	unittest.main()

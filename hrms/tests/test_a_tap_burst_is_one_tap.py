"""Taps seconds apart are one tap, and only the first of them counts.

Norazlin, 4 September 2026: IN 18:09:14, OUT 18:09:26, IN 18:09:30 — three taps
in sixteen seconds. The engine read that as a twelve-second session and a
dangling check-in, so her day came to 2h40m and read Half Day.

Nobody works twelve seconds. That shape is a person tapping again because the
screen told them the wrong thing (fixed separately in CheckInPanel on the same
day), and it must not be able to write a session.

Why the later taps are SKIP-STAMPED and not refused: a refusal is what the old
60-second SAME_PUNCH_WINDOW did, and it was removed because it also refused a
real punch — an employee could then never file a late check-out at all. Nothing
here is lost: the row is stored with its time and its type, it carries a comment
saying why it does not count, and HR can bring it back from Fix Day in one
click. The evidence stays; only its effect on the day is withheld.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_a_tap_burst_is_one_tap.py
"""

from __future__ import annotations

import ast
import pathlib
import unittest
from datetime import datetime, timedelta

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.api import remote_checkin

NOW = datetime(2026, 9, 4, 18, 9, 30)


def ago(seconds, **over):
	row = {"time": NOW - timedelta(seconds=seconds), "log_type": "OUT"}
	row.update(over)
	return row


class BurstCase(unittest.TestCase):
	"""Pure: is this punch part of the burst the one before it started?"""

	def test_four_seconds_after_the_last_tap_is_the_same_tap(self):
		self.assertTrue(remote_checkin.is_burst_tap(ago(4), NOW))

	def test_sixteen_seconds_is_still_the_same_burst(self):
		self.assertTrue(remote_checkin.is_burst_tap(ago(16), NOW))

	def test_a_real_gap_is_a_real_punch(self):
		self.assertFalse(remote_checkin.is_burst_tap(ago(11 * 60), NOW))

	def test_the_edge_of_the_window_counts_as_a_real_punch(self):
		window = int(remote_checkin.BURST_WINDOW.total_seconds())
		self.assertFalse(remote_checkin.is_burst_tap(ago(window), NOW))
		self.assertTrue(remote_checkin.is_burst_tap(ago(window - 1), NOW))

	def test_the_first_tap_of_a_day_has_nothing_before_it(self):
		self.assertFalse(remote_checkin.is_burst_tap(None, NOW))

	def test_a_mirrored_punch_is_not_this_persons_tap(self):
		"""A row copied from the old system never means a finger on this phone."""
		self.assertFalse(remote_checkin.is_burst_tap(ago(4, synced_from_instance="nasty"), NOW))

	def test_a_rejected_punch_does_not_start_a_burst(self):
		self.assertFalse(remote_checkin.is_burst_tap(ago(4, remote_approval_status="Rejected"), NOW))

	def test_a_tap_before_the_last_one_is_not_a_burst(self):
		"""Clock skew must not make a punch swallow itself."""
		self.assertFalse(remote_checkin.is_burst_tap(ago(-30), NOW))


class PunchContractCase(unittest.TestCase):
	"""What `punch` does with a burst tap."""

	def setUp(self):
		tree = ast.parse(pathlib.Path(remote_checkin.__file__).read_text())
		self.punch = ast.unparse(
			next(
				node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "punch"
			)
		)

	def test_the_burst_tap_is_stored_and_not_refused(self):
		"""The old refusal cost an employee their late check-out; never again."""
		burst = self.punch[self.punch.index("is_burst_tap") :]
		self.assertNotIn("frappe.throw", burst.split("doc.insert()")[0])

	def test_it_is_marked_not_counted(self):
		self.assertIn("skip_auto_attendance", self.punch)

	def test_it_says_why_on_the_row_itself(self):
		"""HR reading the punch must see the reason, not just a tick."""
		self.assertIn("add_comment", self.punch)


class HrCanSeeItCase(unittest.TestCase):
	"""A skip nobody is told about is a skip nobody fixes.

	The Attendance Day Audit already lists skip-stamped punches and offers HR
	"unskip" — but only for a skip whose reason it can READ (a comment carrying
	`SKIP_PREFIX`) and recognise (`REPAIRABLE_SKIP_REASONS`). A burst tap that
	was really a short session would otherwise sit uncounted with a comment
	nobody reads, for a whole pay cycle.
	"""

	def test_the_burst_comment_is_one_the_audit_reads(self):
		from hrms.utils.attendance_day_audit import SKIP_PREFIX

		tree = ast.parse(pathlib.Path(remote_checkin.__file__).read_text())
		punch = ast.unparse(
			next(
				node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "punch"
			)
		)
		self.assertTrue(SKIP_PREFIX, "the audit's prefix must exist to be reused")
		self.assertIn(
			"SKIP_PREFIX",
			punch,
			"the comment must carry the audit's own prefix — taken from it, not retyped, "
			"so the two cannot drift apart",
		)

	def test_the_comment_is_written_in_the_type_the_readers_query(self):
		"""Matching the marker strings is not enough — the ROW TYPE must match too.

		`Document.add_comment(comment_type, text)` stores its first argument as
		`Comment.comment_type`, and every reader of a skip reason filters
		`comment_type == "Comment"`. Written as "Info" the row is simply never
		seen, so the audit shows the punch skipped with no reason and no way
		back — the exact thing this comment exists to prevent, passing every
		string-consistency test while doing nothing at all.
		"""
		import re

		source = pathlib.Path(remote_checkin.__file__).read_text()
		burst = source[source.index("BURST_SKIP_REASON") :]
		written = re.search(r'add_comment\(\s*"(\w+)"', burst[burst.index("if burst:") :])
		self.assertIsNotNone(written, "the burst path comments on the row")

		audit = pathlib.Path(
			pathlib.Path(remote_checkin.__file__).parents[1] / "utils" / "attendance_day_audit.py"
		).read_text()
		queried = re.search(r'"comment_type":\s*"(\w+)"', audit)
		self.assertIsNotNone(queried, "the audit queries a comment type")
		self.assertEqual(
			written.group(1),
			queried.group(1),
			"the burst comment must be written in the type the audit reads",
		)

	def test_the_audit_offers_hr_the_way_back(self):
		from hrms.utils.attendance_day_audit import REPAIRABLE_SKIP_REASONS

		self.assertTrue(
			any(remote_checkin.BURST_SKIP_REASON.startswith(key) for key in REPAIRABLE_SKIP_REASONS)
			or remote_checkin.BURST_SKIP_REASON in REPAIRABLE_SKIP_REASONS,
			"a burst skip must be one the audit can offer to undo",
		)


if __name__ == "__main__":
	unittest.main()

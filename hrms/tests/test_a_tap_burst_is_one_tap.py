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


if __name__ == "__main__":
	unittest.main()

"""A missing announcement board must not take the whole month down.

Seen on fresh.local, 23 Sep 2026: HR Announcement was not migrated, so
_event_days raised DoesNotExistError, get_month_flags answered 403, and every
employee's Calendar toasted "Something didn't load" and drew no leave,
holiday or needs-you dots at all. Event dots are the least of four kinds; the
other three must survive without them.

    PYTHONPATH=. python3 -m pytest -q hrms/api/test_calendar_event_dot_soft.py
"""

import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.api import calendar


class TestEventDotFailsSoft(unittest.TestCase):
	def test_no_board_means_no_event_dots_not_an_error(self):
		def boom(reader):
			raise frappe.DoesNotExistError("DocType HR Announcement not found")

		with (
			patch("hrms.api.announcements._reader", return_value=frappe._dict(name="E1")),
			patch("hrms.api.announcements._visible_rows", side_effect=boom),
		):
			self.assertEqual(calendar._event_days("E1", None, None), set())

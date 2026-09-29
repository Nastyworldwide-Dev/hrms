"""Reminders to approvers — the first approver owns the request (owner, 29 Sep
2026: "we want to encourage the first approver to act ... our reminder/
notification is being deliberate ... even if they take approved leave").

Pure planner: given what is waiting and how many working days it has waited,
who hears what today. One summary per approver, never one ping per request.

| waited (working days) | first approver                          | backup (level 2)        |
| 0 (sent)              | nothing new (the "sent" notice exists)  | —                       |
| reminder day (1)      | summary                                 | —                       |
| reminder day + 1 (2)  | summary + "the director can act for you"| —                       |
| backup day (3)        | "X has been asked to help"              | "Ali's leave has waited" |
Leave starting within 2 days skips straight to the backup step on day 1.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_approval_reminders.py
"""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from hrms.utils.approval_reminders import plan_reminders

SETTINGS = {"reminder_after": 1, "backup_after": 3}


def req(name, waited, first="senior@x", backup="director@x", who="Ali", kind="leave", starts_in=None):
	return {
		"name": name,
		"waited": waited,
		"first": first,
		"backup": backup,
		"employee_name": who,
		"kind": kind,
		"first_name": "Senior",
		"backup_name": "Director",
		"starts_in": starts_in,
	}


def plan(*requests, **settings):
	return plan_reminders(list(requests), {**SETTINGS, **settings})


def to(messages, user):
	return [m for m in messages if m["to"] == user]


class TestTheFirstApproverIsRemindedFirst(unittest.TestCase):
	def test_nothing_on_the_day_it_was_sent(self):
		self.assertEqual(plan(req("R1", 0)), [])

	def test_one_summary_the_next_working_day(self):
		out = plan(req("R1", 1), req("R2", 1, who="Siti"))
		self.assertEqual(len(to(out, "senior@x")), 1, "one summary, not one per request")
		self.assertIn("2 requests are waiting for you", to(out, "senior@x")[0]["message"])
		self.assertEqual(to(out, "director@x"), [])

	def test_day_two_says_the_backup_can_act(self):
		out = plan(req("R1", 2))
		self.assertIn("Director can act for you", to(out, "senior@x")[0]["message"])
		self.assertEqual(to(out, "director@x"), [])


class TestTheBackupIsAskedOnlyAfterTheOwnerHadTheirTurn(unittest.TestCase):
	def test_day_three_asks_the_backup_and_tells_the_owner(self):
		out = plan(req("R1", 3))
		self.assertIn("Ali's leave has waited 3 days for Senior", to(out, "director@x")[0]["message"])
		self.assertIn("Director has been asked to help", to(out, "senior@x")[0]["message"])

	def test_leave_starting_soon_asks_the_backup_on_day_one(self):
		out = plan(req("R1", 1, starts_in=1))
		self.assertEqual(len(to(out, "director@x")), 1)

	def test_no_backup_means_only_the_owner_is_reminded(self):
		out = plan(req("R1", 3, backup=None))
		self.assertEqual([m["to"] for m in out], ["senior@x"])


class TestWordsAreHuman(unittest.TestCase):
	def test_one_request_reads_naturally(self):
		out = plan(req("R1", 1))
		self.assertIn("Ali's leave is waiting for you", to(out, "senior@x")[0]["message"])

	def test_no_codes_in_any_message(self):
		for m in plan(req("HR-LAP-2026-00046", 3)):
			self.assertNotIn("HR-", m["message"])


class TestHrSetsTheDays(unittest.TestCase):
	def test_backup_after_two_days(self):
		out = plan(req("R1", 2), backup_after=2)
		self.assertEqual(len(to(out, "director@x")), 1)


if __name__ == "__main__":
	unittest.main()

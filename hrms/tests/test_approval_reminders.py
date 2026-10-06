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
First approver AWAY (approved leave covering today): the backup is asked on
working day 2, and both are told (owner ruling R2, 6 Oct 2026).

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_approval_reminders.py
"""

import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.utils import approval_reminders
from hrms.utils.approval_reminders import plan_reminders

SETTINGS = {"reminder_after": 1, "backup_after": 3}


def req(
	name,
	waited,
	first="senior@x",
	backup="director@x",
	who="Ali",
	kind="leave",
	starts_in=None,
	first_away=False,
):
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
		"first_away": first_away,
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


class TestAnApproverWhoIsAwayDoesNotHoldARequest(unittest.TestCase):
	"""Owner ruling R2, 6 Oct 2026: approved leave covering today means the
	backup is asked after 2 working days, and both people are told."""

	def test_away_and_two_days_asks_the_backup_and_tells_the_owner(self):
		out = plan(req("R1", 2, first_away=True))
		self.assertEqual(
			to(out, "senior@x")[0]["message"],
			"Ali's leave waited 2 days while you are away; Director was asked to decide.",
		)
		self.assertIn("Senior, who is away", to(out, "director@x")[0]["message"])
		self.assertIn("Ali's leave has waited 2 days", to(out, "director@x")[0]["message"])

	def test_away_and_one_day_is_not_yet(self):
		out = plan(req("R1", 1, first_away=True))
		self.assertEqual(to(out, "director@x"), [])
		self.assertIn("Ali's leave is waiting for you", to(out, "senior@x")[0]["message"])

	def test_not_away_and_two_days_keeps_todays_rule(self):
		out = plan(req("R1", 2, first_away=False))
		self.assertEqual(to(out, "director@x"), [])
		self.assertIn("Director can act for you", to(out, "senior@x")[0]["message"])
		out = plan(req("R1", 3, first_away=False))
		self.assertEqual(len(to(out, "director@x")), 1)
		self.assertNotIn("away", to(out, "director@x")[0]["message"])
		self.assertNotIn("away", to(out, "senior@x")[0]["message"])

	def test_away_without_a_backup_tells_only_the_owner(self):
		out = plan(req("R1", 2, backup=None, first_away=True))
		self.assertEqual([m["to"] for m in out], ["senior@x"])
		self.assertIn("waiting for you", out[0]["message"])

	def test_urgent_leave_rule_is_unchanged_when_away(self):
		out = plan(req("R1", 1, starts_in=1, first_away=True))
		self.assertEqual(len(to(out, "director@x")), 1)
		out = plan(req("R2", 1, starts_in=10, first_away=True))
		self.assertEqual(to(out, "director@x"), [])

	def test_hr_setting_below_two_still_wins(self):
		out = plan(req("R1", 1, first_away=True), backup_after=1)
		self.assertEqual(len(to(out, "director@x")), 1)

	def test_many_away_requests_are_still_one_summary_each(self):
		out = plan(req("R1", 2, first_away=True), req("R2", 2, who="Siti", first_away=True))
		self.assertEqual(len(to(out, "senior@x")), 1)
		self.assertEqual(len(to(out, "director@x")), 1)
		self.assertEqual(
			to(out, "senior@x")[0]["message"],
			"2 requests waited while you are away; Director was asked to decide them.",
		)
		self.assertIn("Everyone is away", to(out, "director@x")[0]["message"])

	def test_one_backup_for_an_away_and_a_present_approver(self):
		out = plan(
			req("R1", 2, first="away@x", first_away=True),
			req("R2", 3, first="here@x", who="Siti"),
		)
		self.assertEqual(len(to(out, "director@x")), 1)
		self.assertIn("Some of them are away", to(out, "director@x")[0]["message"])
		self.assertIn("away", to(out, "away@x")[0]["message"])
		self.assertNotIn("away", to(out, "here@x")[0]["message"])


class TestOneMessagePerPersonPerDay(unittest.TestCase):
	"""Owner rule (29 Sep): one summary per person per day, never a ping per
	request. A person who owns one request and is the backup on another got
	TWO notifications (review of W1, 6 Oct; older than W1, made likelier by it)."""

	def test_an_owner_who_is_also_a_backup_gets_one_message_with_both(self):
		out = plan(
			req("R1", 1, first="mid@x", backup="director@x"),  # mid@x owns this one
			req("R2", 3, first="senior@x", backup="mid@x", who="Siti"),  # and backs up this one
		)
		self.assertEqual(len(to(out, "mid@x")), 1)
		message = to(out, "mid@x")[0]["message"]
		self.assertIn("Ali's leave is waiting for you.", message)
		self.assertIn("Siti", message)

	def test_every_person_appears_once(self):
		out = plan(
			req("R1", 3, first="a@x", backup="b@x"),
			req("R2", 3, first="b@x", backup="a@x", who="Siti"),
		)
		users = [m["to"] for m in out]
		self.assertEqual(sorted(users), sorted(set(users)))


class TestHalfDayLeaveIsNotAway(unittest.TestCase):
	"""Review of W1: someone on a half day is at work for the other half and can
	decide; only a full day off counts as away."""

	def _away(self, rows, today="2026-10-06"):
		from unittest.mock import patch

		import hrms.utils.approval_reminders as ar

		with patch.object(ar.frappe, "get_all", return_value=[ar.frappe._dict(r) for r in rows]) as get_all:
			away = ar._away_approvers(today)
		self.assertEqual(get_all.call_count, 1, "still one read")
		return away

	def test_a_half_day_today_is_not_away(self):
		row = {"user_id": "a@x", "half_day": 1, "half_day_date": "2026-10-06"}
		self.assertEqual(self._away([row]), set())

	def test_a_long_leave_with_its_half_day_on_another_date_is_away_today(self):
		# review of the first fix: filtering half_day = 0 dropped the whole of a
		# five-day leave whose LAST day was a half day
		row = {"user_id": "a@x", "half_day": 1, "half_day_date": "2026-10-09"}
		self.assertEqual(self._away([row]), {"a@x"})

	def test_a_one_day_half_day_with_no_date_set_is_not_away(self):
		row = {
			"user_id": "a@x",
			"half_day": 1,
			"half_day_date": None,
			"from_date": "2026-10-06",
			"to_date": "2026-10-06",
		}
		self.assertEqual(self._away([row]), set())


class TestWaitingRequestsReadsLeaveOnce(unittest.TestCase):
	"""`first_away` for every waiting request comes from ONE Leave Application
	read, not one query per request."""

	def _run(self, leave_rows):
		waiting = [
			frappe._dict(
				name=f"L{i}",
				employee=f"EMP-{i}",
				employee_name=f"Emp{i} Z",
				creation="2026-10-01 09:00:00",
				from_date=None,
			)
			for i in range(3)
		]
		firsts = {"EMP-0": "away@x", "EMP-1": "here@x", "EMP-2": "away@x"}
		calls = []

		def get_all(doctype, filters=None, fields=None, **kwargs):
			calls.append((doctype, filters, fields))
			if doctype != "Leave Application":
				return []
			if filters.get("docstatus") == 0:
				return waiting
			return leave_rows

		with (
			patch.object(frappe, "get_all", side_effect=get_all),
			patch.object(frappe, "db") as db,
			patch(
				"hrms.hr.utils.get_designated_approvers",
				side_effect=lambda emp, *_: [firsts[emp], "director@x"],
			),
			patch.object(approval_reminders, "_working_days_between", return_value=2),
			patch.object(approval_reminders, "now_datetime", return_value=datetime(2026, 10, 6, 6, 0)),
		):
			db.exists.return_value = True
			db.get_value.return_value = "Name"
			out = approval_reminders._waiting_requests()
		return out, calls

	def test_one_leave_read_for_many_requests_and_the_flag_is_per_first_approver(self):
		rows = [frappe._dict(user_id="Away@X")]
		out, calls = self._run(rows)
		reads = [c for c in calls if c[0] == "Leave Application" and c[1].get("docstatus") == 1]
		self.assertEqual(len(reads), 1, "one away read, however many requests wait")
		filters = reads[0][1]
		self.assertEqual(filters["status"], "Approved")
		self.assertEqual(filters["from_date"], ["<=", date(2026, 10, 6)])
		self.assertEqual(filters["to_date"], [">=", date(2026, 10, 6)])
		self.assertIn("employee.user_id", " ".join(reads[0][2]))
		self.assertEqual({r["name"]: r["first_away"] for r in out}, {"L0": True, "L1": False, "L2": True})

	def test_nobody_on_leave_means_nobody_away(self):
		out, calls = self._run([])
		self.assertEqual([r["first_away"] for r in out], [False, False, False])
		self.assertEqual(len([c for c in calls if c[1].get("docstatus") == 1]), 1)

	def test_a_leave_row_with_no_login_is_ignored(self):
		out, _ = self._run([frappe._dict(user_id=None)])
		self.assertEqual([r["first_away"] for r in out], [False, False, False])

	def test_nothing_waiting_reads_no_leave(self):
		with (
			patch.object(frappe, "get_all", return_value=[]) as get_all,
			patch.object(frappe, "db") as db,
		):
			db.exists.return_value = True
			self.assertEqual(approval_reminders._waiting_requests(), [])
		self.assertFalse(
			any(
				c.args[0] == "Leave Application" and c.kwargs["filters"].get("docstatus") == 1
				for c in get_all.call_args_list
			)
		)


if __name__ == "__main__":
	unittest.main()

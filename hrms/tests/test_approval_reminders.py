"""Reminders to approvers — the first approver owns the request (owner, 29 Sep
2026: "we want to encourage the first approver to act ... our reminder/
notification is being deliberate ... even if they take approved leave").

Pure planner: given what is waiting and how many working days it has waited,
who hears what today. One summary per approver, never one ping per request.

Owner, 27 Oct 2026: only the first approver is reminded, every working day from
the reminder day until they decide, on leave or not. The backup is never asked
or named. From the third day the message says how long it has waited.

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


class TestOnlyTheFirstApproverIsReminded(unittest.TestCase):
	"""Owner, 27 Oct 2026: "revert the backup approver, we want to encourage the first
	and only approver, approve. that's their job." Replaces the 29 Sep backup step and
	ruling R2 (an away approver hands over after 2 days). The person above may still
	approve if they open the request (HR Settings "Backup approval levels"); the
	reminders never ask them, and never offer them as a way out."""

	def test_the_backup_is_never_messaged_however_long_it_waits(self):
		for waited in (1, 2, 3, 10):
			out = plan(req("R1", waited))
			self.assertEqual([m["to"] for m in out], ["senior@x"], waited)

	def test_the_backup_is_never_named_to_the_owner(self):
		for waited in (1, 2, 3, 10):
			self.assertNotIn("Director", to(plan(req("R1", waited)), "senior@x")[0]["message"])

	def test_leave_starting_soon_still_goes_only_to_the_owner(self):
		out = plan(req("R1", 1, starts_in=1))
		self.assertEqual([m["to"] for m in out], ["senior@x"])

	def test_an_owner_on_leave_is_still_the_one_reminded(self):
		out = plan(req("R1", 4, first_away=True))
		self.assertEqual([m["to"] for m in out], ["senior@x"])

	def test_after_the_first_days_the_owner_hears_how_long_it_has_waited(self):
		self.assertEqual(to(plan(req("R1", 1)), "senior@x")[0]["message"], "Ali's leave is waiting for you.")
		self.assertEqual(
			to(plan(req("R1", 3)), "senior@x")[0]["message"],
			"Ali's leave is waiting for you. It has waited 3 days.",
		)
		self.assertEqual(
			to(plan(req("R1", 3), req("R2", 1, who="Siti")), "senior@x")[0]["message"],
			"2 requests are waiting for you. The oldest has waited 3 days.",
		)

	def test_hr_reminder_day_still_applies(self):
		self.assertEqual(plan(req("R1", 1), reminder_after=2), [])
		self.assertEqual(len(plan(req("R1", 2), reminder_after=2)), 1)


class TestWordsAreHuman(unittest.TestCase):
	def test_one_request_reads_naturally(self):
		out = plan(req("R1", 1))
		self.assertIn("Ali's leave is waiting for you", to(out, "senior@x")[0]["message"])

	def test_no_codes_in_any_message(self):
		for m in plan(req("HR-LAP-2026-00046", 3)):
			self.assertNotIn("HR-", m["message"])


class TestOneMessagePerPersonPerDay(unittest.TestCase):
	"""Owner rule (29 Sep): one summary per person per day, never a ping per request."""

	def test_many_requests_are_one_summary(self):
		out = plan(req("R1", 1), req("R2", 2, who="Siti"), req("R3", 5, who="Amy"))
		self.assertEqual(len(out), 1)

	def test_every_person_appears_once(self):
		out = plan(req("R1", 3, first="a@x"), req("R2", 3, first="b@x", who="Siti"))
		users = [m["to"] for m in out]
		self.assertEqual(sorted(users), ["a@x", "b@x"])


class TestTheDailyJobAsksOnlyTheFirstApprover(unittest.TestCase):
	"""Owner, 27 Oct 2026: the job gathers each waiting request's FIRST approver; it reads
	no leave (being on leave no longer hands a request over) and carries no backup."""

	def _run(self):
		waiting = [
			frappe._dict(
				name=f"L{i}", employee=f"EMP-{i}", employee_name=f"Emp{i} Z", creation="2026-10-01 09:00:00"
			)
			for i in range(2)
		]
		calls = []

		def get_all(doctype, filters=None, fields=None, **kwargs):
			calls.append((doctype, filters))
			return waiting if doctype == "Leave Application" and filters.get("docstatus") == 0 else []

		with (
			patch.object(frappe, "get_all", side_effect=get_all),
			patch.object(frappe, "db") as db,
			patch("hrms.hr.utils.get_designated_approvers", return_value=["senior@x", "director@x"]),
			patch.object(approval_reminders, "_working_days_between", return_value=4),
			patch.object(approval_reminders, "now_datetime", return_value=datetime(2026, 10, 6, 6, 0)),
		):
			db.exists.return_value = True
			out = approval_reminders._waiting_requests()
		return out, calls

	def test_each_request_names_only_its_first_approver(self):
		out, _ = self._run()
		self.assertEqual({r["first"] for r in out}, {"senior@x"})
		self.assertFalse(any("backup" in r for r in out))

	def test_no_leave_is_read_to_decide_who_is_asked(self):
		_, calls = self._run()
		leave_reads = [f for d, f in calls if d == "Leave Application" and f.get("status") == "Approved"]
		self.assertEqual(leave_reads, [])

	def test_the_plan_sends_one_message_to_the_first_approver(self):
		out, _ = self._run()
		plan = plan_reminders(out, {"reminder_after": 1})
		self.assertEqual([m["to"] for m in plan], ["senior@x"])
		self.assertEqual(plan[0]["message"], "2 requests are waiting for you. The oldest has waited 4 days.")


class TestEveryApprovableTypeIsReminded(unittest.TestCase):
	"""Frappe review of aba0a4461: Manpower Request joined DECIDE_THEN_SUBMIT but not KIND_WORDS,
	and _waiting_requests walks KIND_WORDS, so its approver was never reminded. The class: any
	type an approver decides and the reminder list does not name is silently never nudged."""

	# Decided elsewhere, not by a line approver this job reminds (policy: no banked overtime,
	# 23 Sep 2026 — the PWA has no screen for it).
	NOT_REMINDED = frozenset({"Replacement Leave Claim"})

	def test_every_decided_type_has_reminder_words(self):
		from hrms.api.approval import DECIDE_THEN_SUBMIT

		missing = set(DECIDE_THEN_SUBMIT) - set(approval_reminders.KIND_WORDS) - self.NOT_REMINDED
		self.assertEqual(missing, set())

	def test_manpower_request_reads_naturally(self):
		# the Home count already calls it this (needs_you.ROW_COPY); one word everywhere
		self.assertEqual(approval_reminders.KIND_WORDS["Manpower Request"], "manpower request")


if __name__ == "__main__":
	unittest.main()


class TestDailyMeansOnceAndOnTheirWorkingDay(unittest.TestCase):
	"""Review of ecadbe2c9: with a reminder every working day, a second run of the job the
	same day sent a second message, and Saturday's run reached an approver on their day off
	(the waited count skipped rest days; the send did not)."""

	def _send(self, *, already=(), off=(), plan=None):
		plan = plan or [{"to": "a@x", "message": "m"}, {"to": "b@x", "message": "m"}]
		inserted = []

		class _Doc(dict):
			def insert(self, **kw):
				inserted.append(self["to_user"])

		with (
			patch.object(approval_reminders, "_waiting_requests", return_value=[]),
			patch.object(approval_reminders, "plan_reminders", return_value=plan),
			patch.object(approval_reminders, "_setting", return_value=1),
			patch.object(approval_reminders, "_reminded_today", return_value=set(already)),
			patch.object(approval_reminders, "_off_today", side_effect=lambda user: user in off),
			patch.object(frappe, "get_doc", side_effect=lambda d: _Doc(d)),
			patch.object(frappe, "db"),
		):
			sent = approval_reminders.send_daily_reminders()
		return sent, inserted

	def test_an_approver_already_reminded_today_is_not_reminded_again(self):
		sent, inserted = self._send(already={"a@x"})
		self.assertEqual(inserted, ["b@x"])
		self.assertEqual(sent, 1)

	def test_no_reminder_on_the_approvers_own_day_off(self):
		_, inserted = self._send(off={"b@x"})
		self.assertEqual(inserted, ["a@x"])

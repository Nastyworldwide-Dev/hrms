"""Cancelling an APPROVED request tells its approver(s) and HR (owner ruling R3, 6 Oct 2026).

The balance and the attendance are put back by each doctype's own on_cancel; this is only
the notice: "{who} cancelled {employee}'s approved {kind} ({its days, when it has them}). The balance and
attendance were put back." as a PWA Notification, once to each person, never to whoever
cancelled it and never to the employee.

Pinned here, bench-free (frappe stubbed when no bench is on the path):

  * an approved request cancelled -> the approvers on its line and HR, once each, minus
    the person who cancelled and minus the employee, for every decidable doctype;
  * the decision is read from the row as it was BEFORE the cancel: LeaveApplication
    sets status = "Cancelled" in memory before on_cancel runs;
  * a request that was never approved (rejected) tells nobody;
  * a notice that cannot be written is logged and never blocks the cancel, and never
    commits or rolls back the cancel's own transaction;
  * sync / patch / migrate / install contexts stay quiet;
  * hooks.py wires it on on_cancel for every decidable doctype and keeps what was there.

    PYTHONPATH=.:hrms/tests python3 -m pytest -q -p no:cacheprovider hrms/tests/test_cancel_notice.py
"""

import ast
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
for module in ("pypika", "pypika.terms", "pypika.functions"):
	sys.modules.setdefault(module, MagicMock())
from _fake_document import FakeDocument, fake_employees

import frappe

HRMS_ROOT = Path(__file__).resolve().parents[1]
HOOK = "hrms.utils.cancel_notice.notify_cancelled"
LOGGER = "hrms.utils.cancel_notice"

EMPLOYEE = "HR-EMP-0001"
EMPLOYEE_USER = "siti@example.com"
FIRST_APPROVER = "ali@example.com"
BACKUP_APPROVER = "director@example.com"
HR_ONE = "hr1@example.com"
HR_TWO = "hr2@example.com"
FULL_NAMES = {
	FIRST_APPROVER: "Ali Hassan",
	BACKUP_APPROVER: "Dina Director",
	HR_ONE: "Hana HR",
	EMPLOYEE_USER: "Siti Aminah",
}

# From the ruling and the request words, not from the module.
DECISION_FIELD = {
	"Leave Application": "status",
	"Expense Claim": "approval_status",
	"Shift Request": "status",
	"Attendance Request": "status",
	"OT Request": "status",
	"Replacement Leave Claim": "status",
	"Compensatory Leave Request": "status",
}
# The pair approval_reminders and the approval routing hand to get_designated_approvers.
APPROVER_PAIR = {
	"Leave Application": ("leave_approver", "leave_approvers"),
	"Expense Claim": ("expense_approver", "expense_approvers"),
	"Shift Request": ("shift_request_approver", "shift_request_approver"),
	"Attendance Request": ("leave_approver", "leave_approvers"),
	"OT Request": ("leave_approver", "leave_approvers"),
	"Replacement Leave Claim": ("leave_approver", "leave_approvers"),
	"Compensatory Leave Request": ("leave_approver", "leave_approvers"),
}
KIND = {
	"Leave Application": "leave",
	"Expense Claim": "expense",
	"Shift Request": "shift change",
	"Attendance Request": "day fix",
	"OT Request": "overtime claim",
	"Replacement Leave Claim": "replacement leave claim",
	"Compensatory Leave Request": "time-off-in-lieu request",
}
# Every on_cancel handler that was wired BEFORE this notice, per doctype.
EXISTING_ON_CANCEL = {
	"Leave Application": ["hrms.overrides.day_remark_hooks.remark_request_days"],
	"Attendance Request": ["hrms.overrides.day_remark_hooks.remark_request_days"],
}


class _Request(FakeDocument):
	"""A request at on_cancel. `_before` is the row as the database held it before the
	cancel (Document.get_doc_before_save); the in-memory fields are what the controller
	left, which for a Leave Application is already status = "Cancelled"."""

	def get_doc_before_save(self):
		return self._before


def _request(doctype="Leave Application", before="Approved", in_memory=None, **fields):
	field = DECISION_FIELD[doctype]
	row = {
		"name": f"{doctype}-0001",
		"employee": EMPLOYEE,
		"employee_name": "Siti Aminah",
		"company": "Company A",
		"docstatus": 2,
		"from_date": "2026-09-15",
		"to_date": "2026-09-15",
		field: before if in_memory is None else in_memory,
		**fields,
	}
	return _Request(doctype, _before=FakeDocument(doctype, **{field: before}), **row)


def _db():
	employees = fake_employees({EMPLOYEE: {"user_id": EMPLOYEE_USER, "company": "Company A"}})

	def get_value(doctype, name=None, fieldname=None, *args, **kwargs):
		if doctype == "User":
			return FULL_NAMES.get(name) if fieldname == "full_name" else None
		return employees(doctype, name, fieldname, *args, **kwargs)

	db = MagicMock()
	db.get_value.side_effect = get_value
	return db


def _cancel(
	doc,
	session_user=FIRST_APPROVER,
	chain=(FIRST_APPROVER, BACKUP_APPROVER),
	hr=(HR_ONE, HR_TWO),
	flags=None,
	fail_for=(),
	chain_error=None,
	hr_error=None,
):
	"""Run the hook as `session_user`. Returns (the PWA Notification rows inserted, the
	get_designated_approvers mock, the db mock)."""
	from hrms.utils import cancel_notice

	sent = []

	def get_doc(values):
		row = MagicMock()

		def insert(**kwargs):
			if values["to_user"] in fail_for:
				raise RuntimeError("cannot write the notification")
			sent.append(values)

		row.insert.side_effect = insert
		return row

	db = _db()
	with (
		patch.object(frappe, "db", db),
		patch.object(frappe, "session", frappe._dict(user=session_user), create=True),
		patch.object(frappe, "flags", frappe._dict(flags or {}), create=True),
		patch.object(frappe, "get_doc", side_effect=get_doc),
		patch(
			"hrms.hr.utils.get_designated_approvers", return_value=list(chain), side_effect=chain_error
		) as designated,
		patch(
			"hrms.overrides.remote_checkin_request_hooks.hr_alert_recipients",
			return_value=list(hr),
			side_effect=hr_error,
		),
	):
		cancel_notice.notify_cancelled(doc, "on_cancel")
	return sent, designated, db


def _told(sent):
	return sorted(row["to_user"] for row in sent)


class TestWhoIsTold(unittest.TestCase):
	def test_the_other_approver_and_hr_hear_once_each_not_the_canceller(self):
		sent, _designated, _db = _cancel(_request(), session_user=FIRST_APPROVER)
		self.assertEqual(_told(sent), sorted([BACKUP_APPROVER, HR_ONE, HR_TWO]))

	def test_an_employee_withdrawing_their_own_tells_the_line_and_hr_not_themselves(self):
		sent, _designated, _db = _cancel(
			_request(), session_user=EMPLOYEE_USER, hr=(HR_ONE, EMPLOYEE_USER, HR_TWO)
		)
		self.assertEqual(_told(sent), sorted([FIRST_APPROVER, BACKUP_APPROVER, HR_ONE, HR_TWO]))

	def test_hr_cancelling_is_not_told_their_own_cancel(self):
		sent, _designated, _db = _cancel(_request(), session_user=HR_ONE)
		self.assertEqual(_told(sent), sorted([FIRST_APPROVER, BACKUP_APPROVER, HR_TWO]))

	def test_a_person_who_is_approver_and_hr_hears_once(self):
		sent, _designated, _db = _cancel(
			_request(), session_user=EMPLOYEE_USER, chain=(FIRST_APPROVER,), hr=(FIRST_APPROVER, HR_ONE)
		)
		self.assertEqual(_told(sent), sorted([FIRST_APPROVER, HR_ONE]))

	def test_logins_that_differ_only_in_case_are_one_person(self):
		sent, _designated, _db = _cancel(
			_request(),
			session_user=EMPLOYEE_USER,
			chain=(FIRST_APPROVER,),
			hr=(FIRST_APPROVER.upper(), "  Siti@Example.com ", HR_ONE),
		)
		self.assertEqual(_told(sent), sorted([FIRST_APPROVER, HR_ONE]))

	def test_an_employee_with_no_login_still_gets_the_notice_to_the_others(self):
		doc = _request(employee="HR-EMP-NOUSER")
		sent, _designated, _db = _cancel(doc, session_user=HR_ONE)
		self.assertEqual(_told(sent), sorted([FIRST_APPROVER, BACKUP_APPROVER, HR_TWO]))

	def test_hr_is_resolved_inside_the_requests_company_fence(self):
		from hrms.utils import cancel_notice

		with patch("hrms.overrides.remote_checkin_request_hooks.hr_alert_recipients") as hr_alert:
			hr_alert.return_value = []
			with (
				patch.object(frappe, "db", _db()),
				patch.object(frappe, "session", frappe._dict(user=FIRST_APPROVER), create=True),
				patch.object(frappe, "flags", frappe._dict(), create=True),
				patch.object(frappe, "get_doc", return_value=MagicMock()),
				patch("hrms.hr.utils.get_designated_approvers", return_value=[]),
			):
				cancel_notice.notify_cancelled(_request())
		hr_alert.assert_called_once_with("Company A")


class TestWhatTheyAreTold(unittest.TestCase):
	def test_plain_words_with_who_whom_what_and_when(self):
		sent, _designated, _db = _cancel(_request(), session_user=FIRST_APPROVER)
		message = sent[0]["message"]
		self.assertIn(
			"Ali Hassan cancelled Siti Aminah's approved leave (Tue 15 Sep). "
			"The balance and attendance were put back.",
			message,
		)

	def test_when_is_the_request_s_own_dates_not_the_moment_of_cancelling(self):
		# found live on fresh.local, 6 Oct: the notice said the cancel time, so an
		# approver could not tell which of a person's leaves had gone
		doc = _request(from_date="2026-09-15", to_date="2026-09-17")
		sent, _designated, _db = _cancel(doc, session_user=FIRST_APPROVER)
		self.assertIn("(Tue 15 Sep – Thu 17 Sep)", sent[0]["message"])
		ot = _request("OT Request", ot_date="2026-09-20")
		sent, _designated, _db = _cancel(ot, session_user=FIRST_APPROVER)
		self.assertIn("(Sun 20 Sep)", sent[0]["message"])

	def test_a_request_with_no_dates_says_no_empty_brackets(self):
		doc = _request("Expense Claim")
		sent, _designated, _db = _cancel(doc, session_user=FIRST_APPROVER)
		self.assertNotIn("()", sent[0]["message"])

	def test_the_notice_opens_the_request_and_comes_from_whoever_cancelled(self):
		doc = _request()
		sent, _designated, _db = _cancel(doc, session_user=FIRST_APPROVER)
		row = sent[0]
		self.assertEqual(row["doctype"], "PWA Notification")
		self.assertEqual(row["from_user"], FIRST_APPROVER)
		self.assertEqual(row["reference_document_type"], "Leave Application")
		self.assertEqual(row["reference_document_name"], doc.name)
		self.assertEqual(row["read"], 0)

	def test_the_message_is_escaped_for_the_rich_text_field(self):
		doc = _request(employee_name="Ali <b> & Sons")
		sent, _designated, _db = _cancel(doc, session_user=HR_ONE)
		self.assertIn("Ali &lt;b&gt; &amp; Sons", sent[0]["message"])
		self.assertNotIn("<b>", sent[0]["message"])


class TestEveryDecidableRequestType(unittest.TestCase):
	def test_each_approved_type_is_told_with_its_own_line_and_words(self):
		for doctype in DECISION_FIELD:
			with self.subTest(doctype=doctype):
				sent, designated, _db = _cancel(_request(doctype), session_user=FIRST_APPROVER)
				self.assertEqual(_told(sent), sorted([BACKUP_APPROVER, HR_ONE, HR_TWO]))
				designated.assert_called_once_with(EMPLOYEE, *APPROVER_PAIR[doctype])
				self.assertIn(f"approved {KIND[doctype]}", sent[0]["message"])
				self.assertEqual(sent[0]["reference_document_type"], doctype)


class TestOnlyAnApprovedRequestIsReported(unittest.TestCase):
	def test_a_rejected_request_that_is_cancelled_tells_nobody(self):
		for doctype in DECISION_FIELD:
			with self.subTest(doctype=doctype):
				sent, designated, _db = _cancel(_request(doctype, before="Rejected"))
				self.assertEqual(sent, [])
				designated.assert_not_called()

	def test_an_undecided_request_tells_nobody(self):
		for before in ("Open", "Draft"):
			with self.subTest(before=before):
				sent, _designated, _db = _cancel(_request(before=before))
				self.assertEqual(sent, [])

	def test_a_leave_the_controller_already_marked_cancelled_still_counts_when_it_was_approved(self):
		# LeaveApplication.before_cancel sets status = "Cancelled" before on_cancel runs:
		# the decision has to come from the row as it was.
		sent, _designated, _db = _cancel(_request(before="Approved", in_memory="Cancelled"))
		self.assertEqual(len(sent), 3)

	def test_a_leave_that_was_rejected_stays_quiet_though_it_now_reads_cancelled(self):
		sent, _designated, _db = _cancel(_request(before="Rejected", in_memory="Cancelled"))
		self.assertEqual(sent, [])

	def test_a_doctype_that_is_not_decidable_tells_nobody(self):
		doc = _Request("Employee Advance", name="EA-1", employee=EMPLOYEE, status="Approved", _before=None)
		sent, _designated, _db = _cancel(doc)
		self.assertEqual(sent, [])


class TestAFailedNoticeNeverBlocksTheCancel(unittest.TestCase):
	def test_an_insert_that_raises_is_logged_and_the_others_still_hear(self):
		with self.assertLogs(LOGGER, level="ERROR") as logged:
			sent, _designated, _db = _cancel(_request(), fail_for=(HR_ONE,))
		self.assertEqual(_told(sent), sorted([BACKUP_APPROVER, HR_TWO]))
		self.assertTrue(any(HR_ONE in line for line in logged.output), logged.output)

	def test_every_insert_failing_is_logged_and_nothing_is_raised(self):
		with self.assertLogs(LOGGER, level="ERROR") as logged:
			sent, _designated, _db = _cancel(_request(), fail_for=(BACKUP_APPROVER, HR_ONE, HR_TWO))
		self.assertEqual(sent, [])
		self.assertGreaterEqual(len(logged.output), 3)

	def test_a_line_that_cannot_be_resolved_is_logged_and_hr_is_still_told(self):
		with self.assertLogs(LOGGER, level="ERROR") as logged:
			sent, _designated, _db = _cancel(_request(), chain_error=RuntimeError("no line"))
		self.assertEqual(_told(sent), sorted([HR_ONE, HR_TWO]))
		self.assertTrue(any("Leave Application" in line for line in logged.output), logged.output)

	def test_hr_that_cannot_be_resolved_is_logged_and_the_line_is_still_told(self):
		with self.assertLogs(LOGGER, level="ERROR") as logged:
			sent, _designated, _db = _cancel(
				_request(), session_user=EMPLOYEE_USER, hr_error=RuntimeError("no hr")
			)
		self.assertEqual(_told(sent), sorted([FIRST_APPROVER, BACKUP_APPROVER]))
		self.assertTrue(any("Leave Application" in line for line in logged.output), logged.output)

	def test_a_database_read_that_raises_is_logged_and_the_cancel_still_goes_through(self):
		from hrms.utils import cancel_notice

		db = MagicMock()
		db.get_value.side_effect = RuntimeError("database went away")
		with (
			self.assertLogs(LOGGER, level="ERROR") as logged,
			patch.object(frappe, "db", db),
			patch.object(frappe, "session", frappe._dict(user=FIRST_APPROVER), create=True),
			patch.object(frappe, "flags", frappe._dict(), create=True),
		):
			cancel_notice.notify_cancelled(_request(), "on_cancel")
		self.assertTrue(any("Leave Application-0001" in line for line in logged.output), logged.output)

	def test_it_never_commits_or_rolls_back_the_cancels_own_transaction(self):
		with self.assertLogs(LOGGER, level="ERROR"):
			_sent, _designated, db = _cancel(_request(), fail_for=(HR_ONE,))
		db.commit.assert_not_called()
		db.rollback.assert_not_called()


class TestQuietContexts(unittest.TestCase):
	def test_sync_patch_migrate_install_send_nothing(self):
		for flag in ("in_shadow_sync", "in_patch", "in_migrate", "in_install"):
			with self.subTest(flag=flag):
				sent, designated, _db = _cancel(_request(), flags={flag: True})
				self.assertEqual(sent, [])
				designated.assert_not_called()


class TestHooksWiring(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		tree = ast.parse((HRMS_ROOT / "hooks.py").read_text(encoding="utf-8"))
		cls.doc_events = next(
			node.value
			for node in ast.walk(tree)
			if isinstance(node, ast.Assign)
			and any(getattr(t, "id", None) == "doc_events" for t in node.targets)
		)

	def _events(self, doctype):
		for key, value in zip(self.doc_events.keys, self.doc_events.values, strict=True):
			if isinstance(key, ast.Constant) and key.value == doctype:
				return ast.literal_eval(value)
		return {}

	def _on_cancel(self, doctype):
		handlers = self._events(doctype).get("on_cancel", [])
		return [handlers] if isinstance(handlers, str) else handlers

	def test_the_notice_runs_on_cancel_for_every_decidable_doctype(self):
		for doctype in DECISION_FIELD:
			with self.subTest(doctype=doctype):
				handlers = self._on_cancel(doctype)
				self.assertEqual(handlers.count(HOOK), 1, f"{doctype}: {handlers}")
				for existing in EXISTING_ON_CANCEL.get(doctype, []):
					self.assertIn(existing, handlers, f"{doctype}: merging dropped {existing}")

	def test_a_new_decidable_doctype_cannot_be_left_without_the_notice(self):
		from hrms.api.approval import DECIDE_THEN_SUBMIT

		self.assertEqual(set(DECISION_FIELD), set(DECIDE_THEN_SUBMIT))

	def test_each_doctype_still_has_one_entry_and_its_other_events(self):
		keys = [k.value for k in self.doc_events.keys if isinstance(k, ast.Constant)]
		self.assertEqual(sorted({k for k in keys if keys.count(k) > 1}), [])
		for doctype in DECISION_FIELD:
			with self.subTest(doctype=doctype):
				before_cancel = self._events(doctype).get("before_cancel", [])
				before_cancel = [before_cancel] if isinstance(before_cancel, str) else before_cancel
				self.assertIn("hrms.utils.approved_request_guard.block_cancel_of_approved", before_cancel)


if __name__ == "__main__":
	unittest.main()

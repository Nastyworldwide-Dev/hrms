"""Manpower Request after it is sent: who is told, who may withdraw, what HR may set, the tracker.

Bench-free (frappe stubbed when no bench is on the path). Expected values come from the owner's
rulings of 22 Oct 2026 (manpower-plan.md rounds 1-2) and the S2 brief, not from the code:

  * HR is told when it is SENT (FYI) and when the line APPROVES (action), once each, minus the sender;
  * the requester is told on every decision and whenever HR changes the hiring status;
  * the sender withdraws while Open, or Approved and still Waiting for HR / Recruiting; never
    otherwise; the record is kept; the line approver (if still Open) and HR are told;
  * a plain save can never set Withdrawn, and the sender can never decide their own request;
  * hiring status: Approved requests only; Filled / Not proceeding are final bar System Manager;
    Not proceeding needs a note;
  * the tracker: Sent -> Manager -> HR -> Filled, each step with who, when and a state.

    PYTHONPATH=.:hrms/tests python3 -m pytest -q -p no:cacheprovider hrms/hr/doctype/manpower_request/test_manpower_request_flow.py
"""

import ast
import sys
import unittest
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

HRMS_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HRMS_ROOT / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
from _fake_document import fake_employees

import frappe

from hrms.api import approval, approvals_list
from hrms.hr.doctype.manpower_request import manpower_request as mr
from hrms.hr.doctype.manpower_request.test_manpower_request import _Request
from hrms.mixins import pwa_notifications
from hrms.utils import decision_field_guard as guard

REQUESTER_USER = "hafiz@example.com"
BOSS_USER = "boss@example.com"
HR_USER = "hana@example.com"
HR_OTHER = "hadi@example.com"


class _Flow(_Request):
	"""A request with the bits a saved Document has that the notices and guards read."""

	def __init__(self, **fields):
		fields.setdefault("flags", frappe._dict())
		fields.setdefault("company", "NASTY")
		fields.setdefault("name", "HR-MPR-26-10-00001")
		before = fields.pop("before", None)
		super().__init__(**fields)
		object.__setattr__(self, "_before_save", before)

	def has_value_changed(self, fieldname):
		before = self._before_save
		return True if not before else before.get(fieldname) != self.get(fieldname)


def before(**fields):
	return frappe._dict(fields)


class Notices:
	"""The PWA Notifications a controller inserted, in order."""

	def __init__(self):
		self.sent = []

	def new_doc(self, doctype):
		assert doctype == "PWA Notification", doctype
		notice = SimpleNamespace(doctype=doctype)
		notice.insert = lambda ignore_permissions=False: self.sent.append(notice)
		return notice

	def to(self, user):
		return [n for n in self.sent if n.to_user == user]

	def users(self):
		return [n.to_user for n in self.sent]


def world(*, hr=(HR_USER, HR_OTHER), user=BOSS_USER, roles=("Employee",), employees=None, users=None):
	"""What the notices and rules read: HR recipients, the session, the Employee and User rows."""
	notices = Notices()
	db = MagicMock()
	people = {"EMP-HAFIZ": {"user_id": REQUESTER_USER, "company": "NASTY", "employee_name": "Hafiz"}}
	people.update(employees or {})
	db.get_value.side_effect = _get_value(fake_employees(people), users or {})
	stack = ExitStack()
	stack.enter_context(patch.object(frappe, "db", db))
	stack.enter_context(patch.object(frappe, "session", MagicMock(user=user)))
	stack.enter_context(patch.object(frappe, "new_doc", notices.new_doc))
	stack.enter_context(patch.object(frappe, "get_roles", return_value=list(roles), create=True))
	stack.enter_context(patch.object(mr, "hr_alert_recipients", return_value=list(hr)))
	# `bold` and `escape_html` are MagicMocks under the shared stub (as in test_no_lie_from_a_decided_draft)
	stack.enter_context(patch.object(pwa_notifications, "bold", str))
	stack.enter_context(
		patch(
			"frappe.utils.escape_html",
			lambda t: str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
			create=True,
		)
	)
	return stack, notices, db


def _get_value(employees, users):
	def get_value(doctype, name=None, fieldname=None, *args, **kwargs):
		if doctype == "User":
			return users.get(name, name)
		return employees(doctype, name, fieldname, *args, **kwargs)

	return get_value


class TestHrIsToldWhenItIsSent(unittest.TestCase):
	def _send(self, approvers=(BOSS_USER,), **fields):
		doc = _Flow(**fields)
		stack, notices, _ = world(user=REQUESTER_USER, users={BOSS_USER: "Aiman Yusof"})
		with (
			stack,
			patch.object(mr, "get_designated_approvers", return_value=list(approvers)),
			patch.object(mr, "share_doc_with_approver"),
			patch.object(mr.ManpowerRequest, "notify_approver"),
		):
			doc.after_insert()
		return notices

	def test_every_hr_user_gets_one_plain_notice_naming_who_is_waited_on(self):
		notices = self._send(headcount=2, position_title="Welder", department="Ops")
		self.assertEqual(sorted(notices.users()), [HR_OTHER, HR_USER])
		message = notices.to(HR_USER)[0].message
		self.assertIn("Hafiz asked for Welder ×2 (Ops). Waiting for Aiman Yusof.", message)

	def test_the_notice_points_at_the_request(self):
		notice = self._send().to(HR_USER)[0]
		self.assertEqual(
			(notice.reference_document_type, notice.reference_document_name),
			("Manpower Request", "HR-MPR-26-10-00001"),
		)

	def test_the_sender_is_never_told_even_when_they_are_HR(self):
		doc = _Flow()
		stack, notices, _ = world(hr=(HR_USER, REQUESTER_USER), user=REQUESTER_USER)
		with (
			stack,
			patch.object(mr, "get_designated_approvers", return_value=[BOSS_USER]),
			patch.object(mr, "share_doc_with_approver"),
			patch.object(mr.ManpowerRequest, "notify_approver"),
		):
			doc.after_insert()
		self.assertEqual(notices.users(), [HR_USER])

	def test_no_one_on_the_line_still_tells_hr_without_a_name(self):
		notices = self._send(approvers=())
		self.assertIn("Waiting for their manager.", notices.to(HR_USER)[0].message)

	def test_the_company_fence_is_asked_with_the_requests_company(self):
		doc = _Flow(company="NASTY Logistics")
		stack, _, _ = world(user=REQUESTER_USER)
		with (
			stack,
			patch.object(mr, "get_designated_approvers", return_value=[]),
			patch.object(mr, "share_doc_with_approver"),
			patch.object(mr.ManpowerRequest, "notify_approver"),
			patch.object(mr, "hr_alert_recipients", return_value=[]) as recipients,
		):
			doc.after_insert()
		recipients.assert_called_once_with("NASTY Logistics")

	def test_hr_lookup_failing_never_undoes_the_send(self):
		# Frappe review of aba0a4461: _notify_hr ran outside the notice guard, so a bad
		# User Permission row raising in hr_alert_recipients failed the insert itself.
		doc = _Flow()
		stack, notices, _ = world(user=REQUESTER_USER)
		with (
			stack,
			patch.object(mr, "get_designated_approvers", return_value=[BOSS_USER]),
			patch.object(mr, "share_doc_with_approver"),
			patch.object(mr.ManpowerRequest, "notify_approver"),
			patch.object(mr, "hr_alert_recipients", side_effect=RuntimeError("bad fence row")),
		):
			doc.after_insert()
		self.assertEqual(notices.users(), [])


class TestDecisionNotices(unittest.TestCase):
	def _submit(self, status, **extra):
		doc = _Flow(docstatus=1, status=status, **extra)
		stack, notices, _ = world(user=BOSS_USER, users={BOSS_USER: "Aiman Yusof"})
		with stack, patch.object(mr, "validate_self_submission"):
			doc.on_submit()
		return doc, notices

	def test_approval_tells_the_requester_and_hr(self):
		doc, notices = self._submit("Approved", headcount=3, position_title="Driver")
		self.assertEqual(sorted(notices.users()), sorted([REQUESTER_USER, HR_USER, HR_OTHER]))
		self.assertIn("has been", notices.to(REQUESTER_USER)[0].message)
		self.assertIn("Approved", notices.to(REQUESTER_USER)[0].message)
		self.assertIn("Aiman Yusof approved Driver ×3 for Hafiz. Your turn.", notices.to(HR_USER)[0].message)
		self.assertEqual(doc.hiring_status, "Waiting for HR")

	def test_rejection_tells_the_requester_with_the_reason_and_not_hr(self):
		doc = _Flow(docstatus=1, status="Rejected")
		doc.flags.rejection_reason = "Budget is frozen"
		stack, notices, _ = world(user=BOSS_USER)
		with stack, patch.object(mr, "validate_self_submission"):
			doc.on_submit()
		self.assertEqual(notices.users(), [REQUESTER_USER])
		self.assertIn("Budget is frozen", notices.to(REQUESTER_USER)[0].message)


class TestThePlainSaveCanNeverWithdraw(unittest.TestCase):
	def test_a_save_that_sets_withdrawn_is_refused(self):
		for was in ("Open", "Approved", None):
			with self.subTest(was=was):
				doc = _Flow(status="Withdrawn", before=before(status=was) if was else None)
				with self.assertRaises(frappe.PermissionError) as caught:
					doc.validate_not_withdrawn_by_save()
				self.assertIn("Withdraw", str(caught.exception))

	def test_an_already_withdrawn_request_may_be_saved_again(self):
		doc = _Flow(status="Withdrawn", before=before(status="Withdrawn"))
		doc.validate_not_withdrawn_by_save()

	def test_other_statuses_are_not_this_checks_business(self):
		for status in ("Open", "Approved", "Rejected"):
			_Flow(status=status, before=before(status="Open")).validate_not_withdrawn_by_save()


class TestWhoMayWithdrawAndWhen(unittest.TestCase):
	def _withdraw(self, reason=None, user=REQUESTER_USER, approvers=(BOSS_USER,), **fields):
		doc = _Flow(**fields)
		stack, notices, _ = world(user=user, users={BOSS_USER: "Aiman Yusof"})
		with stack, patch.object(mr, "get_designated_approvers", return_value=list(approvers)):
			doc.withdraw(reason)
		return doc, notices

	def test_an_open_draft_can_be_withdrawn_and_the_record_is_kept(self):
		doc, _ = self._withdraw("Role covered by a transfer.", docstatus=0, status="Open")
		self.assertEqual(doc.status, "Withdrawn")
		self.assertEqual(doc.withdrawn_reason, "Role covered by a transfer.")
		self.assertEqual(doc.docstatus, 0)
		self.assertIsNotNone(doc.withdrawn_at)
		self.assertNotIn("delete", doc.methods_run)

	def test_only_the_sender_can_withdraw_and_hr_does_not(self):
		for user in ("junior@example.com", HR_USER, BOSS_USER):
			with self.subTest(user=user):
				doc = _Flow(docstatus=0, status="Open")
				stack, notices, _ = world(user=user, roles=("Employee", "HR Manager"))
				with stack, patch.object(mr, "is_own_employee", return_value=False):
					with self.assertRaises(frappe.PermissionError):
						doc.withdraw("not mine")
				self.assertEqual(doc.db_writes, [])
				self.assertEqual((doc.status, notices.sent), ("Open", []))

	def test_an_approved_request_is_withdrawable_while_waiting_or_recruiting(self):
		for hiring in ("Waiting for HR", "Recruiting"):
			with self.subTest(hiring=hiring):
				doc, _ = self._withdraw(docstatus=1, status="Approved", hiring_status=hiring)
				self.assertEqual(doc.status, "Withdrawn")
				self.assertEqual(doc.docstatus, 1)

	def test_nothing_else_can_be_withdrawn(self):
		cases = [
			dict(docstatus=1, status="Approved", hiring_status="Filled"),
			dict(docstatus=1, status="Approved", hiring_status="Not proceeding"),
			dict(docstatus=1, status="Rejected"),
			dict(docstatus=0, status="Withdrawn"),
			dict(docstatus=1, status="Withdrawn", hiring_status="Recruiting"),
			dict(docstatus=2, status="Approved", hiring_status="Recruiting"),
		]
		for fields in cases:
			with self.subTest(**fields):
				doc = _Flow(**fields)
				stack, notices, _ = world(user=REQUESTER_USER)
				with stack, self.assertRaises(frappe.ValidationError):
					doc.withdraw("changed my mind")
				self.assertEqual(doc.db_writes, [])
				self.assertEqual(notices.sent, [])

	def test_the_reason_is_trimmed_and_capped_at_500(self):
		doc, _ = self._withdraw("  " + "x" * 700 + "  ", docstatus=0, status="Open")
		self.assertEqual(doc.withdrawn_reason, "x" * 500)

	def test_a_blank_reason_is_stored_as_nothing(self):
		doc, _ = self._withdraw("   ", docstatus=0, status="Open")
		self.assertIsNone(doc.withdrawn_reason)

	def test_it_writes_without_validate_so_no_decision_guard_is_involved(self):
		doc, _ = self._withdraw(docstatus=1, status="Approved", hiring_status="Recruiting")
		written = dict(doc.db_writes)
		self.assertEqual(written["status"], "Withdrawn")
		self.assertNotIn("validate", doc.methods_run)

	def test_the_line_approver_and_hr_are_told_while_it_was_still_open(self):
		_, notices = self._withdraw(docstatus=0, status="Open", headcount=2, position_title="Welder")
		self.assertEqual(sorted(notices.users()), sorted([BOSS_USER, HR_USER, HR_OTHER]))
		self.assertIn("Hafiz withdrew the request for Welder ×2.", notices.to(BOSS_USER)[0].message)
		self.assertIn("Hafiz withdrew the request for Welder ×2.", notices.to(HR_USER)[0].message)

	def test_once_approved_only_hr_is_told(self):
		_, notices = self._withdraw(
			docstatus=1, status="Approved", hiring_status="Recruiting", headcount=1, position_title="Cook"
		)
		self.assertEqual(sorted(notices.users()), sorted([HR_USER, HR_OTHER]))


class TestHiringStatusRules(unittest.TestCase):
	def _change(self, was, now, *, status="Approved", note=None, roles=("HR User",)):
		doc = _Flow(
			docstatus=1,
			status=status,
			hiring_status=now,
			hr_note=note,
			before=before(hiring_status=was, status=status),
		)
		stack, _, _ = world(user=HR_USER, roles=roles)
		with stack:
			doc.before_update_after_submit()
		return doc

	def refuses(self, *args, **kwargs):
		with self.assertRaises(frappe.ValidationError) as caught:
			self._change(*args, **kwargs)
		return str(caught.exception)

	def test_the_normal_road_is_allowed(self):
		self._change("Waiting for HR", "Recruiting")
		self._change("Recruiting", "Filled")
		self._change("Recruiting", "Not proceeding", note="Hiring freeze until January")

	def test_only_an_approved_request_has_a_hiring_status(self):
		for status in ("Rejected", "Withdrawn", "Open"):
			with self.subTest(status=status):
				self.assertIn("approved", self.refuses(None, "Recruiting", status=status))

	def test_not_proceeding_needs_a_note(self):
		for note in (None, "", "   "):
			with self.subTest(note=note):
				self.assertIn("why", self.refuses("Recruiting", "Not proceeding", note=note).lower())

	def test_filled_and_not_proceeding_are_final(self):
		for final in ("Filled", "Not proceeding"):
			with self.subTest(final=final):
				self.assertIn("closed", self.refuses(final, "Recruiting", note="x"))

	def test_a_system_manager_can_reopen_a_closed_one(self):
		self._change("Filled", "Recruiting", roles=("System Manager",))

	def test_a_hiring_status_cannot_be_blanked(self):
		self.assertIn("Pick", self.refuses("Recruiting", None))

	def test_an_edit_that_leaves_the_hiring_status_alone_is_not_checked(self):
		self._change("Filled", "Filled", note="late note")


class TestRequesterToldWhenHrChangesHiring(unittest.TestCase):
	def _updated(self, was, now, note=None, user=HR_USER):
		doc = _Flow(
			docstatus=1,
			status="Approved",
			hiring_status=now,
			hr_note=note,
			before=before(hiring_status=was),
		)
		stack, notices, _ = world(user=user)
		with stack:
			doc.on_update_after_submit()
		return notices

	def test_a_change_tells_the_requester_with_the_note(self):
		notices = self._updated("Waiting for HR", "Recruiting", note="Posting it on Monday")
		self.assertEqual(notices.users(), [REQUESTER_USER])
		# answer first, then the note (design review of aba0a4461: the record id led the line)
		self.assertIn("HR is recruiting for Welder ×2.", notices.to(REQUESTER_USER)[0].message)
		self.assertNotIn("HR-MPR-", notices.to(REQUESTER_USER)[0].message)
		self.assertIn("Posting it on Monday", notices.to(REQUESTER_USER)[0].message)

	def test_no_note_no_trailing_text(self):
		message = self._updated("Recruiting", "Filled").to(REQUESTER_USER)[0].message
		self.assertIn("Welder ×2 is filled.", message)
		self.assertNotIn("None", message)

	def test_not_proceeding_says_so_with_hrs_reason(self):
		message = (
			self._updated("Recruiting", "Not proceeding", note="Budget moved to Q1")
			.to(REQUESTER_USER)[0]
			.message
		)
		self.assertIn("HR is not proceeding with Welder ×2: Budget moved to Q1", message)

	def test_one_person_needs_no_count(self):
		doc = _Flow(
			docstatus=1,
			status="Approved",
			hiring_status="Recruiting",
			headcount=1,
			position_title="Cook",
			before=before(hiring_status="Waiting for HR"),
		)
		stack, notices, _ = world(user=HR_USER)
		with stack:
			doc.on_update_after_submit()
		self.assertIn("HR is recruiting for Cook.", notices.to(REQUESTER_USER)[0].message)

	def test_the_note_is_escaped(self):
		message = self._updated("Recruiting", "Not proceeding", note="<b>x</b>").to(REQUESTER_USER)[0].message
		self.assertNotIn("<b>x</b>", message)

	def test_an_unchanged_value_tells_nobody(self):
		self.assertEqual(self._updated("Recruiting", "Recruiting").sent, [])

	def test_hr_who_is_also_the_requester_is_not_told_of_their_own_change(self):
		self.assertEqual(self._updated("Recruiting", "Filled", user=REQUESTER_USER).sent, [])


class TestTheSenderCannotDecideTheirOwnRequest(unittest.TestCase):
	"""The Employee DocPerm lets the sender write their own draft, and `read_only` is a Desk rule.
	The decision-field guard, now wired for this doctype, is what stops a set_value."""

	def _guard(self, now, *, was="Open", user=REQUESTER_USER, own=False, routed=False, changed=True):
		doc = _Flow(status=now, before=before(status=was))
		if not changed:
			doc.has_value_changed = lambda fieldname: False
		with (
			patch.object(frappe, "db", MagicMock()),
			patch.object(frappe, "session", frappe._dict(user=user)),
			patch.object(frappe, "flags", frappe._dict(), create=True),
			patch.object(frappe, "has_permission", return_value=False, create=True),
			patch.object(approval, "is_own_employee", return_value=own),
			patch.object(approval, "_request_read_allowed", return_value=True),
			patch.object(approval, "_is_routed_approver", return_value=routed),
			patch("frappe.model.workflow.get_workflow_name", return_value=None),
		):
			guard.validate(doc)

	def test_the_sender_saving_approved_rejected_or_withdrawn_is_refused(self):
		for value in ("Approved", "Rejected", "Withdrawn"):
			with self.subTest(value=value), self.assertRaises(frappe.PermissionError):
				self._guard(value, own=True)

	def test_the_sender_may_still_edit_other_fields_of_their_open_draft(self):
		self._guard("Open", own=True, changed=False)

	def test_the_line_approver_still_decides_through_decide(self):
		doc = _Flow(status="Open", docstatus=0, modified="2026-10-22 10:00:00")
		doc.submit = lambda: (guard.validate(doc), doc.set("docstatus", 1))
		doc.has_value_changed = lambda fieldname: True
		object.__setattr__(doc, "_before_save", before(status="Open"))
		db = MagicMock()
		db.exists.return_value = True
		db.get_value.return_value = 0
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_doc", return_value=doc),
			patch.object(frappe, "session", frappe._dict(user=BOSS_USER)),
			patch.object(frappe, "flags", frappe._dict(), create=True),
			patch.object(frappe, "has_permission", return_value=False, create=True),
			patch.object(approval, "is_own_employee", return_value=False),
			patch.object(approval, "_request_read_allowed", return_value=True),
			patch.object(approval, "_is_routed_approver", return_value=True),
			patch("frappe.model.workflow.get_workflow_name", return_value=None),
		):
			state = approval.decide(
				"Manpower Request", doc.name, "Approved", expected_modified="2026-10-22 10:00:00"
			)
		self.assertEqual((state["status"], state["docstatus"]), ("Approved", 1))

	def test_decide_refuses_a_withdrawn_request(self):
		for docstatus, status in ((0, "Withdrawn"), (1, "Withdrawn")):
			with self.subTest(docstatus=docstatus):
				doc = _Flow(status=status, docstatus=docstatus, modified="2026-10-22 10:00:00")
				db = MagicMock()
				db.exists.return_value = True
				db.get_value.return_value = 0
				with (
					patch.object(frappe, "db", db),
					patch.object(frappe, "get_doc", return_value=doc),
					patch.object(frappe, "session", frappe._dict(user=BOSS_USER)),
					patch.object(approval, "_decision_access", return_value="routed"),
					self.assertRaises(frappe.ValidationError),
				):
					approval.decide("Manpower Request", doc.name, "Approved", expected_modified=doc.modified)
				self.assertEqual(doc.status, "Withdrawn")


class TestTheRegistries(unittest.TestCase):
	def test_it_is_an_approvable_request_shaped_like_compensatory_leave(self):
		self.assertEqual(approval.DECIDE_THEN_SUBMIT["Manpower Request"], ("status", "Open"))
		self.assertEqual(
			approval.DESIGNATED_APPROVER_DOCTYPES["Manpower Request"], ("leave_approver", "leave_approvers")
		)
		self.assertEqual(
			approval.DESIGNATED_APPROVER_DOCTYPES["Manpower Request"],
			approval.DESIGNATED_APPROVER_DOCTYPES["Compensatory Leave Request"],
		)

	def test_approvals_list_dates_and_kind(self):
		self.assertEqual(approvals_list.OWN_DATES["Manpower Request"], ("creation", "creation"))
		self.assertEqual(approvals_list.KIND["Manpower Request"], "Manpower")

	def test_the_approver_row_reads_position_headcount_department(self):
		doc = _Flow(
			employee_name="Hafiz",
			creation="2026-10-22 09:41:00",
			modified="2026-10-22 09:41:00",
			justification="Two jobs are waiting",
		)
		row = approvals_list._row(doc, {"login": None, "employee": None}, {"EMP-HAFIZ": {}})
		self.assertEqual(row["kind"], "Manpower")
		self.assertEqual(row["detail"], "Welder ×2 · Ops")
		self.assertEqual(row["reason"], "Two jobs are waiting")
		self.assertEqual((row["from_date"], row["to_date"]), ("2026-10-22", "2026-10-22"))

	def test_home_row_copy_and_route(self):
		source = (HRMS_ROOT / "api" / "needs_you.py").read_text()
		tree = ast.parse(source)
		copy = next(
			ast.literal_eval(n.value)
			for n in tree.body
			if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "ROW_COPY"
		)
		self.assertEqual(
			copy["Manpower Request"], ("manpower request", "manpower requests", "ManpowerRequestListView")
		)

	def test_the_notification_status_field_is_status(self):
		self.assertEqual(_Flow()._get_doc_status_field(), "status")
		self.assertTrue(issubclass(mr.ManpowerRequest, pwa_notifications.PWANotificationsMixin))

	def test_the_filing_check_and_push_deep_link(self):
		from hrms.api import filing_check
		from hrms.hr.doctype.pwa_notification import pwa_notification

		self.assertIn("Manpower Request", filing_check.FILABLE)
		self.assertEqual(pwa_notification.PWA_DETAIL_PATHS["Manpower Request"], "manpower-requests")

	def test_it_is_on_the_requests_panel_chips_because_the_panel_lists_it(self):
		# S2 kept it off the chips while the app had no list for it (a chip must count only what the
		# panel shows). S3 adds the list (frontend/src/data/requestLists.js), so the chips count it,
		# and a withdrawn one in no chip (test_request_counts pins both).
		from hrms.api import request_counts

		self.assertIn("Manpower Request", request_counts.LISTED_TYPES)
		js = (HRMS_ROOT.parent / "frontend/src/data/requestLists.js").read_text()
		self.assertIn('"Manpower Request": { my: myManpowerRequests', js)

	def test_hooks_wire_the_guard_the_cancel_notice_and_the_approved_guard(self):
		tree = ast.parse((HRMS_ROOT / "hooks.py").read_text())
		events = next(
			node.value
			for node in ast.walk(tree)
			if isinstance(node, ast.Assign)
			and any(getattr(t, "id", None) == "doc_events" for t in node.targets)
		)
		wired = {}
		for key, value in zip(events.keys, events.values, strict=True):
			if isinstance(key, ast.Constant) and key.value == "Manpower Request":
				wired = ast.literal_eval(value)
		self.assertEqual(wired.get("validate"), "hrms.utils.decision_field_guard.validate")
		self.assertEqual(wired.get("on_cancel"), "hrms.utils.cancel_notice.notify_cancelled")
		self.assertEqual(
			wired.get("before_cancel"), "hrms.utils.approved_request_guard.block_cancel_of_approved"
		)
		self.assertNotIn("block_mirrored_writes", str(wired), "not mirrored")

	def test_the_approved_guard_actually_covers_it(self):
		# the hook above is inert for a doctype the guard's own map does not list
		from hrms.utils import approved_request_guard

		self.assertEqual(approved_request_guard.DECISION_FIELD_BY_DOCTYPE["Manpower Request"], "status")


class TestDeskWording(unittest.TestCase):
	def test_the_why_question_is_asked_in_plain_words(self):
		import json

		meta = json.loads((HRMS_ROOT / "hr/doctype/manpower_request/manpower_request.json").read_text())
		label = next(f["label"] for f in meta["fields"] if f["fieldname"] == "justification")
		self.assertEqual(label, "Why do you need this hire?")

	def test_withdrawing_is_not_a_decision_so_it_needs_no_editable_status(self):
		import json

		meta = json.loads((HRMS_ROOT / "hr/doctype/manpower_request/manpower_request.json").read_text())
		fields = {f["fieldname"]: f for f in meta["fields"]}
		self.assertFalse(fields["status"].get("allow_on_submit"))
		self.assertTrue(fields["withdrawn_at"].get("read_only"))


class TestTheTracker(unittest.TestCase):
	def request(self, **fields):
		base = dict(
			employee_name="Hafiz Rahman",
			creation="2026-10-20 09:12:00",
			status="Open",
			docstatus=0,
			hiring_status=None,
			hr_note=None,
			headcount=2,
			approver_name="Aiman Yusof",
			rejection_reason=None,
			withdrawn_reason=None,
			withdrawn_at=None,
		)
		base.update(fields)
		return base

	def change(self, field, new, by, at, old=None):
		return dict(field=field, old=old, new=new, by=by, at=at)

	def steps(self, request, changes=()):
		return {s["key"]: s for s in mr.build_progress(request, list(changes))}

	def test_the_steps_come_in_order_with_the_keys_the_page_reads(self):
		out = mr.build_progress(self.request(), [])
		self.assertEqual([s["key"] for s in out], ["sent", "manager", "hr", "filled"])
		for step in out:
			self.assertEqual(
				set(step), {"key", "label", "who", "at", "state", "note"}, "the page reads exactly these"
			)

	def test_open_the_manager_is_next(self):
		s = self.steps(self.request())
		self.assertEqual(
			(s["sent"]["state"], s["sent"]["who"], s["sent"]["at"]),
			("done", "Hafiz Rahman", "2026-10-20 09:12:00"),
		)
		self.assertEqual((s["manager"]["state"], s["manager"]["who"]), ("current", "Aiman Yusof"))
		self.assertEqual((s["hr"]["state"], s["filled"]["state"]), ("waiting", "waiting"))

	def test_approved_waiting_for_hr(self):
		s = self.steps(
			self.request(status="Approved", docstatus=1, hiring_status="Waiting for HR"),
			[self.change("status", "Approved", "Aiman Yusof", "2026-10-21 10:05:00", "Open")],
		)
		self.assertEqual(
			(s["manager"]["state"], s["manager"]["who"], s["manager"]["at"]),
			("done", "Aiman Yusof", "2026-10-21 10:05:00"),
		)
		self.assertEqual(s["hr"]["state"], "current")
		self.assertEqual(s["filled"]["state"], "waiting")

	def test_waiting_for_hr_names_nobody_yet(self):
		# the Version that set "Waiting for HR" was written by the approver's submit; it is not HR's act
		s = self.steps(
			self.request(status="Approved", docstatus=1, hiring_status="Waiting for HR"),
			[
				self.change("status", "Approved", "Aiman Yusof", "2026-10-21 10:05:00", "Open"),
				self.change("hiring_status", "Waiting for HR", "Aiman Yusof", "2026-10-21 10:05:00"),
			],
		)
		self.assertEqual((s["hr"]["who"], s["hr"]["at"]), (None, None))

	def test_recruiting_names_who_and_when_hr_moved_it(self):
		s = self.steps(
			self.request(status="Approved", docstatus=1, hiring_status="Recruiting"),
			[
				self.change("status", "Approved", "Aiman Yusof", "2026-10-21 10:05:00", "Open"),
				self.change("hiring_status", "Recruiting", "Hana Ismail", "2026-10-21 15:10:00"),
			],
		)
		self.assertEqual(
			(s["hr"]["state"], s["hr"]["who"], s["hr"]["at"]),
			("current", "Hana Ismail", "2026-10-21 15:10:00"),
		)

	def test_filled_closes_both_last_steps(self):
		s = self.steps(
			self.request(status="Approved", docstatus=1, hiring_status="Filled"),
			[
				self.change("status", "Approved", "Aiman Yusof", "2026-10-21 10:05:00", "Open"),
				self.change("hiring_status", "Recruiting", "Hana Ismail", "2026-10-21 15:10:00"),
				self.change("hiring_status", "Filled", "Hana Ismail", "2026-10-30 11:00:00", "Recruiting"),
			],
		)
		self.assertEqual((s["hr"]["state"], s["filled"]["state"]), ("done", "done"))
		self.assertEqual((s["filled"]["who"], s["filled"]["at"]), ("Hana Ismail", "2026-10-30 11:00:00"))

	def test_not_proceeding_stops_at_hr_with_the_note(self):
		s = self.steps(
			self.request(
				status="Approved",
				docstatus=1,
				hiring_status="Not proceeding",
				hr_note="Hiring freeze until January",
			),
			[
				self.change("status", "Approved", "Aiman Yusof", "2026-10-21 10:05:00", "Open"),
				self.change("hiring_status", "Not proceeding", "Hana Ismail", "2026-10-22 09:00:00"),
			],
		)
		self.assertEqual((s["hr"]["state"], s["hr"]["note"]), ("rejected", "Hiring freeze until January"))
		self.assertEqual(s["filled"]["state"], "waiting")

	def test_rejected_stops_at_the_manager_with_the_reason(self):
		s = self.steps(
			self.request(status="Rejected", docstatus=1, rejection_reason="Budget is frozen"),
			[self.change("status", "Rejected", "Aiman Yusof", "2026-10-21 10:05:00", "Open")],
		)
		self.assertEqual((s["manager"]["state"], s["manager"]["note"]), ("rejected", "Budget is frozen"))
		self.assertEqual((s["hr"]["state"], s["filled"]["state"]), ("waiting", "waiting"))

	def test_withdrawn_while_open_stops_at_the_manager(self):
		s = self.steps(
			self.request(
				status="Withdrawn",
				docstatus=0,
				withdrawn_reason="Role covered",
				withdrawn_at="2026-10-20 10:00:00",
			)
		)
		self.assertEqual((s["manager"]["state"], s["manager"]["note"]), ("withdrawn", "Role covered"))
		self.assertEqual((s["manager"]["who"], s["manager"]["at"]), ("Hafiz Rahman", "2026-10-20 10:00:00"))
		self.assertEqual((s["hr"]["state"], s["filled"]["state"]), ("waiting", "waiting"))

	def test_withdrawn_after_approval_stops_at_hr(self):
		s = self.steps(
			self.request(
				status="Withdrawn",
				docstatus=1,
				hiring_status="Recruiting",
				withdrawn_reason="No longer needed",
				withdrawn_at="2026-10-25 09:00:00",
			),
			[
				self.change("status", "Approved", "Aiman Yusof", "2026-10-21 10:05:00", "Open"),
				self.change("hiring_status", "Recruiting", "Hana Ismail", "2026-10-21 15:10:00"),
			],
		)
		self.assertEqual(s["manager"]["state"], "done")
		self.assertEqual((s["hr"]["state"], s["hr"]["note"]), ("withdrawn", "No longer needed"))
		self.assertEqual(s["filled"]["state"], "waiting")

	def test_a_missing_note_is_none_not_the_word_none(self):
		for step in mr.build_progress(self.request(), []):
			self.assertIsNone(step["note"])


if __name__ == "__main__":
	unittest.main()

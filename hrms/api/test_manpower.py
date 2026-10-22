"""Manpower Request read API: may I ask, and what do I answer.

`can_request` is the controller's team rule (HR may; otherwise an active direct report);
`get_questions` is the settings' active questions in the order HR set, for the wizard.
Bench-free: frappe is stubbed when no bench is on the path.

    PYTHONPATH=.:hrms/tests python3 -m pytest -q -p no:cacheprovider hrms/api/test_manpower.py
"""

import ast
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

HRMS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HRMS_ROOT / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
from _fake_document import FakeDocument

import frappe

from hrms.api import manpower


def question(idx, text, **extra):
	row = dict(
		idx=idx,
		step="5 Requirements",
		question=text,
		answer_type="Short text",
		choices=None,
		required=0,
		help=None,
		active=1,
	)
	row.update(extra)
	return frappe._dict(row)


def settings(*rows):
	return FakeDocument("Manpower Request Settings", questions=list(rows))


class TestCanRequest(unittest.TestCase):
	def _ask(self, *, employee="EMP-HAFIZ", team=True, hr=False):
		db = MagicMock()
		db.exists.return_value = team
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "session", MagicMock(user="hafiz@example.com")),
			patch.object(manpower, "get_employee", return_value=employee),
			patch(
				"hrms.hr.doctype.manpower_request.manpower_request.sees_all_employee_data", return_value=hr
			),
		):
			return manpower.can_request(), db

	def test_someone_with_a_team_can(self):
		answer, db = self._ask(team=True)
		self.assertTrue(answer)
		self.assertEqual(db.exists.call_args.args[1], {"reports_to": "EMP-HAFIZ", "status": "Active"})

	def test_someone_without_a_team_cannot(self):
		self.assertFalse(self._ask(team=False)[0])

	def test_a_login_with_no_employee_cannot(self):
		self.assertFalse(self._ask(employee=None, team=True)[0])

	def test_hr_can_without_a_team(self):
		self.assertTrue(self._ask(employee=None, team=False, hr=True)[0])


class TestGetQuestions(unittest.TestCase):
	def _ask(self, doc):
		with patch.object(frappe, "get_cached_doc", return_value=doc) as getter:
			return manpower.get_questions(), getter

	def test_only_active_questions_in_the_order_hr_set(self):
		doc = settings(
			question(3, "Third"),
			question(1, "First"),
			question(2, "Hidden", active=0),
		)
		answer, getter = self._ask(doc)
		self.assertEqual([q["question"] for q in answer], ["First", "Third"])
		getter.assert_called_once_with("Manpower Request Settings")

	def test_the_step_is_its_number(self):
		answer, _ = self._ask(
			settings(question(1, "A", step="3 Why"), question(2, "B", step="5 Requirements"))
		)
		self.assertEqual([q["step"] for q in answer], [3, 5])

	def test_choices_are_one_per_line_without_blanks(self):
		answer, _ = self._ask(
			settings(
				question(1, "Pick", answer_type="Choice", choices="Diploma\n  Bachelor's Degree \n\nSPM")
			)
		)
		self.assertEqual(answer[0]["choices"], ["Diploma", "Bachelor's Degree", "SPM"])

	def test_a_question_without_choices_has_an_empty_list(self):
		answer, _ = self._ask(settings(question(1, "Say")))
		self.assertEqual(answer[0]["choices"], [])

	def test_what_the_wizard_needs_and_nothing_more(self):
		answer, _ = self._ask(
			settings(question(1, "Say", required=1, help="Be brief", answer_type="Long text"))
		)
		self.assertEqual(
			answer[0],
			{
				"step": 5,
				"question": "Say",
				"answer_type": "Long text",
				"choices": [],
				"required": 1,
				"help": "Be brief",
			},
		)

	def test_no_settings_rows_is_an_empty_list(self):
		self.assertEqual(self._ask(settings())[0], [])


class TestEndpointsAreReadsOnly(unittest.TestCase):
	def test_both_answer_get_and_post_like_every_read_the_pwa_calls(self):
		# The PWA's request layer POSTs by default (resourceConfig.js); has_team and is_approver
		# allow both verbs for that reason. A GET-only endpoint would answer the app 405.
		tree = ast.parse((HRMS_ROOT / "api" / "manpower.py").read_text(encoding="utf-8"))
		found = {}
		for node in tree.body:
			if not isinstance(node, ast.FunctionDef):
				continue
			for deco in node.decorator_list:
				if isinstance(deco, ast.Call) and ast.unparse(deco.func) == "frappe.whitelist":
					methods = [kw.value for kw in deco.keywords if kw.arg == "methods"]
					found[node.name] = ast.literal_eval(methods[0]) if methods else None
		self.assertEqual(
			set(found), {"can_request", "get_questions", "get_progress", "withdraw", "set_hiring_status"}
		)
		for name in ("can_request", "get_questions", "get_progress"):
			self.assertEqual(sorted(found[name] or []), ["GET", "POST"], name)
		# a change of state is never a GET
		for name in ("withdraw", "set_hiring_status"):
			self.assertEqual(found[name], ["POST"], name)

	def test_the_reads_write_nothing(self):
		tree = ast.parse((HRMS_ROOT / "api" / "manpower.py").read_text(encoding="utf-8"))
		reads = {"can_request", "get_questions", "get_progress"}
		for node in tree.body:
			if isinstance(node, ast.FunctionDef) and node.name in reads:
				body = ast.unparse(node)
				for call in (
					".insert(",
					".save(",
					".submit(",
					"db.set_value",
					"db.sql",
					".db_set(",
					"delete_doc",
					".withdraw(",
				):
					self.assertNotIn(call, body, f"{node.name} must not write")


def request_doc(**fields):
	values = dict(
		name="HR-MPR-26-10-00001",
		employee="EMP-HAFIZ",
		employee_name="Hafiz Rahman",
		company="NASTY",
		creation="2026-10-20 09:12:00",
		status="Open",
		docstatus=0,
		hiring_status=None,
		hr_note=None,
		withdrawn_reason=None,
		withdrawn_at=None,
		flags=frappe._dict(),
	)
	values.update(fields)
	doc = FakeDocument("Manpower Request", **values)
	doc.withdraw = MagicMock(name="withdraw")
	doc.save = MagicMock(name="save")
	doc.check_permission = MagicMock(name="check_permission")
	return doc


class TestWithdraw(unittest.TestCase):
	def _call(self, doc, reason="no longer needed"):
		db = MagicMock()
		db.exists.return_value = True
		with patch.object(frappe, "db", db), patch.object(frappe, "get_doc", return_value=doc) as getter:
			result = manpower.withdraw(doc.name, reason)
		return result, getter, db

	def test_it_asks_the_request_to_withdraw_with_the_reason_and_returns_the_new_state(self):
		doc = request_doc()
		doc.withdraw.side_effect = lambda reason: doc.set("status", "Withdrawn")
		result, getter, _ = self._call(doc)
		getter.assert_called_once_with("Manpower Request", doc.name)
		doc.withdraw.assert_called_once_with("no longer needed")
		self.assertEqual(result, {"name": doc.name, "status": "Withdrawn"})

	def test_the_row_is_locked_before_it_is_read(self):
		_, _, db = self._call(request_doc())
		db.get_value.assert_called_once_with(
			"Manpower Request", "HR-MPR-26-10-00001", "docstatus", for_update=True
		)

	def test_a_refusal_from_the_request_reaches_the_caller_and_nothing_is_returned(self):
		doc = request_doc()
		doc.withdraw.side_effect = frappe.PermissionError(
			"Only the person who sent this request can withdraw it."
		)
		with self.assertRaises(frappe.PermissionError):
			self._call(doc)

	def test_a_missing_request_is_not_found(self):
		db = MagicMock()
		db.exists.return_value = False
		with patch.object(frappe, "db", db), self.assertRaises(frappe.DoesNotExistError):
			manpower.withdraw("HR-MPR-NOPE")


class TestSetHiringStatus(unittest.TestCase):
	def _call(self, doc, *, hr=True, visible=True, note=None, status="Recruiting"):
		db = MagicMock()
		db.exists.return_value = True
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_doc", return_value=doc),
			patch.object(manpower, "is_hr_operator", return_value=hr),
			patch.object(manpower, "company_visible", return_value=visible) as fence,
		):
			result = manpower.set_hiring_status(doc.name, status, note)
		return result, fence

	def test_hr_sets_it_by_saving_the_document_so_the_rules_and_the_notice_run(self):
		doc = request_doc(docstatus=1, status="Approved", hiring_status="Waiting for HR")
		result, fence = self._call(doc, note="Posting on Monday")
		self.assertEqual((doc.hiring_status, doc.hr_note), ("Recruiting", "Posting on Monday"))
		doc.save.assert_called_once_with()
		fence.assert_called_once_with("NASTY")
		self.assertEqual(result, {"name": doc.name, "hiring_status": "Recruiting"})

	def test_no_note_leaves_the_earlier_note_alone(self):
		doc = request_doc(docstatus=1, status="Approved", hr_note="First note")
		self._call(doc)
		self.assertEqual(doc.hr_note, "First note")

	def test_a_blank_note_is_not_stored(self):
		doc = request_doc(docstatus=1, status="Approved", hr_note="First note")
		self._call(doc, note="   ")
		self.assertEqual(doc.hr_note, "First note")

	def test_only_hr_may_even_when_they_can_read_it(self):
		doc = request_doc(docstatus=1, status="Approved")
		with self.assertRaises(frappe.PermissionError):
			self._call(doc, hr=False)
		doc.save.assert_not_called()

	def test_hr_outside_the_requests_company_is_refused(self):
		doc = request_doc(docstatus=1, status="Approved")
		with self.assertRaises(frappe.PermissionError):
			self._call(doc, visible=False)
		doc.save.assert_not_called()

	def test_a_missing_request_is_not_found(self):
		db = MagicMock()
		db.exists.return_value = False
		with patch.object(frappe, "db", db), self.assertRaises(frappe.DoesNotExistError):
			manpower.set_hiring_status("HR-MPR-NOPE", "Recruiting")


class TestGetProgress(unittest.TestCase):
	def _call(self, doc, *, allowed=True, versions=(), approvers=("boss@example.com",), reason=None):
		db = MagicMock()
		db.exists.return_value = True
		names = {"boss@example.com": "Aiman Yusof", "hana@example.com": "Hana Ismail"}
		db.get_value.side_effect = lambda doctype, name=None, fieldname=None, *a, **k: (
			names.get(name) if doctype == "User" else None
		)

		def get_all(doctype, filters=None, fields=None, **kw):
			if doctype == "Version":
				return [frappe._dict(v) for v in versions]
			return [frappe._dict(name=u, full_name=n) for u, n in names.items()]

		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_doc", return_value=doc),
			patch.object(frappe, "get_all", side_effect=get_all),
			patch.object(frappe, "has_permission", return_value=allowed, create=True) as perm,
			patch.object(manpower, "get_designated_approvers", return_value=list(approvers)),
			patch.object(manpower, "get_rejection_reason", return_value=reason),
		):
			return manpower.get_progress(doc.name), perm

	def test_it_is_refused_unless_the_caller_may_read_the_request(self):
		with self.assertRaises(frappe.PermissionError):
			self._call(request_doc(), allowed=False)

	def test_the_read_check_is_on_this_request(self):
		_, perm = self._call(request_doc())
		self.assertEqual(perm.call_args.args[:2], ("Manpower Request", "read"))
		self.assertEqual(perm.call_args.kwargs["doc"].name, "HR-MPR-26-10-00001")

	def test_open_names_the_line_approver_as_the_current_step(self):
		steps, _ = self._call(request_doc())
		manager = next(s for s in steps if s["key"] == "manager")
		self.assertEqual((manager["state"], manager["who"]), ("current", "Aiman Yusof"))

	def test_who_and_when_come_from_the_recorded_history(self):
		versions = [
			dict(
				owner="boss@example.com",
				creation="2026-10-21 10:05:00",
				data='{"changed": [["status", "Open", "Approved"], ["modified", "a", "b"]]}',
			),
			dict(
				owner="hana@example.com",
				creation="2026-10-21 15:10:00",
				data='{"changed": [["hiring_status", "Waiting for HR", "Recruiting"]]}',
			),
		]
		doc = request_doc(docstatus=1, status="Approved", hiring_status="Recruiting")
		steps, _ = self._call(doc, versions=versions)
		by_key = {s["key"]: s for s in steps}
		self.assertEqual(
			(by_key["manager"]["who"], by_key["manager"]["at"]), ("Aiman Yusof", "2026-10-21 10:05:00")
		)
		self.assertEqual((by_key["hr"]["state"], by_key["hr"]["who"]), ("current", "Hana Ismail"))

	def test_a_rejection_carries_the_reason_the_approver_gave(self):
		doc = request_doc(docstatus=1, status="Rejected")
		steps, _ = self._call(doc, reason="Budget is frozen")
		self.assertEqual(next(s for s in steps if s["key"] == "manager")["note"], "Budget is frozen")

	def test_a_version_that_is_not_json_is_skipped_not_fatal(self):
		versions = [dict(owner="boss@example.com", creation="2026-10-21 10:05:00", data="not json")]
		steps, _ = self._call(request_doc(), versions=versions)
		self.assertEqual(len(steps), 4)


class TestChangesFromVersions(unittest.TestCase):
	def test_only_the_decision_and_hiring_fields_are_kept_oldest_first(self):
		versions = [
			frappe._dict(
				owner="a@x",
				creation="2026-10-21 10:00:00",
				data='{"changed": [["status", "Open", "Approved"], ["modified", "1", "2"]]}',
			),
			frappe._dict(
				owner="b@x",
				creation="2026-10-22 10:00:00",
				data='{"changed": [["hiring_status", null, "Recruiting"]]}',
			),
		]
		self.assertEqual(
			manpower.changes_from_versions(versions, {"a@x": "Ann", "b@x": "Bo"}),
			[
				{
					"field": "status",
					"old": "Open",
					"new": "Approved",
					"by": "Ann",
					"at": "2026-10-21 10:00:00",
				},
				{
					"field": "hiring_status",
					"old": None,
					"new": "Recruiting",
					"by": "Bo",
					"at": "2026-10-22 10:00:00",
				},
			],
		)

	def test_an_unknown_owner_shows_their_login(self):
		versions = [
			frappe._dict(
				owner="z@x",
				creation="2026-10-21 10:00:00",
				data='{"changed": [["status", "Open", "Approved"]]}',
			)
		]
		self.assertEqual(manpower.changes_from_versions(versions, {})[0]["by"], "z@x")


if __name__ == "__main__":
	unittest.main()

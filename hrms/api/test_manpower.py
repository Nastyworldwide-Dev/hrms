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
		self.assertEqual(set(found), {"can_request", "get_questions"})
		for name, methods in found.items():
			self.assertEqual(sorted(methods or []), ["GET", "POST"], name)

	def test_neither_writes(self):
		source = (HRMS_ROOT / "api" / "manpower.py").read_text(encoding="utf-8")
		for call in (".insert(", ".save(", ".submit(", "db.set_value", "db.sql", ".db_set(", "delete_doc"):
			self.assertNotIn(call, source)


if __name__ == "__main__":
	unittest.main()

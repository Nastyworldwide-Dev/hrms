"""The Manpower Request questions HR can later change are seeded once, from the MS form.

Bench-free:
    PYTHONPATH=.:hrms/tests python3 -m pytest -q -p no:cacheprovider hrms/tests/test_seed_manpower_request_questions_patch.py
"""

import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
from _fake_document import FakeDocument

import frappe

from hrms.patches.v16_0 import seed_manpower_request_questions as patch_module


class _Settings(FakeDocument):
	"""Settings single with a child table: append() and save() like a Document."""

	def __init__(self, questions=None):
		super().__init__("Manpower Request Settings", questions=list(questions or []))
		self.saves = 0

	def append(self, fieldname, row):
		self.get(fieldname).append(frappe._dict(row))

	def save(self, *args, **kwargs):
		self.saves += 1


def run(settings):
	with patch.object(patch_module.frappe, "get_doc", return_value=settings) as get_doc:
		patch_module.execute()
	return get_doc


class TestSeedManpowerRequestQuestions(unittest.TestCase):
	def test_an_empty_settings_gets_the_seven_form_questions(self):
		settings = _Settings()
		run(settings)
		rows = settings.questions
		self.assertEqual(settings.saves, 1)
		self.assertEqual(
			[(r.question, r.step, r.answer_type, r.required) for r in rows],
			[
				("Draft job description", "5 Requirements", "Long text", 1),
				("KPIs", "5 Requirements", "Long text", 0),
				("Minimum qualification", "5 Requirements", "Choice", 0),
				("Experience", "5 Requirements", "Choice", 0),
				("Industry experience required", "5 Requirements", "Choice", 0),
				("If other, which industry", "5 Requirements", "Short text", 0),
				("What happens if it is late?", "3 Why", "Long text", 0),
			],
		)

	def test_the_choices_are_the_forms_one_per_line(self):
		rows = {r.question: r for r in self._seeded()}
		self.assertEqual(
			rows["Minimum qualification"].choices.split("\n"),
			["Diploma", "Bachelor's Degree", "Professional Certification", "SPM / O' Level"],
		)
		self.assertEqual(
			rows["Experience"].choices.split("\n"),
			["Fresh Graduate", "1–3 years", "3–5 years", "5+ years"],
		)
		self.assertEqual(rows["Industry experience required"].choices.split("\n"), ["Yes", "No", "Other"])
		self.assertFalse(rows["Draft job description"].choices)

	def test_every_seeded_question_is_active(self):
		self.assertTrue(all(r.active == 1 for r in self._seeded()))

	def test_settings_that_already_have_questions_are_left_alone(self):
		mine = frappe._dict(
			question="HR's own", step="1 Position", answer_type="Short text", required=0, active=1
		)
		settings = _Settings([mine])
		run(settings)
		self.assertEqual(settings.questions, [mine])
		self.assertEqual(settings.saves, 0)

	def test_a_second_run_changes_nothing(self):
		settings = _Settings()
		run(settings)
		after_first = [dict(r) for r in settings.questions]
		run(settings)
		self.assertEqual([dict(r) for r in settings.questions], after_first)
		self.assertEqual(settings.saves, 1)

	def test_the_patch_is_listed_after_the_model_sync_with_a_dated_comment(self):
		text = (pathlib.Path(__file__).resolve().parents[1] / "patches.txt").read_text()
		self.assertIn("[post_model_sync]", text)
		post = text.split("[post_model_sync]", 1)[1]
		line = next(
			(
				l
				for l in post.splitlines()
				if l.startswith("hrms.patches.v16_0.seed_manpower_request_questions")
			),
			None,
		)
		self.assertIsNotNone(line, "patch not registered after [post_model_sync]")
		self.assertRegex(line, r"#2026-10-22 \S")

	def _seeded(self):
		settings = _Settings()
		run(settings)
		return settings.questions


if __name__ == "__main__":
	unittest.main()

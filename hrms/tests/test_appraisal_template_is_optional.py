"""An appraisal may be made without an Appraisal Template (owner, 3 Nov 2026).

The owner's screenshot: Ilhan's appraisal in Desk, "Appraisal Template *", a
required field with nothing to put in it. Asked where the requirement should go,
the answer was the Appraisal AND the Appraisal Cycle. So:

* the Appraisal form no longer marks the template required once saved
  (`mandatory_depends_on` is gone from the field);
* an Appraisal Cycle creates appraisals for employees with no template, instead
  of refusing the whole batch; their goals start empty, to be filled in by hand;
* Employee Performance Feedback on such an appraisal starts with no criteria,
  instead of crashing on `get_doc("Appraisal Template", None)`.

Rules lifted by AST, so this runs without a bench:

    PYTHONPATH=. python3 hrms/tests/test_appraisal_template_is_optional.py
"""

import ast
import json
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

HR = pathlib.Path(__file__).resolve().parent.parent / "hr" / "doctype"
APPRAISAL_JSON = HR / "appraisal" / "appraisal.json"
CYCLE = HR / "appraisal_cycle" / "appraisal_cycle.py"
FEEDBACK = HR / "employee_performance_feedback" / "employee_performance_feedback.py"


class _Refused(Exception):
	pass


def _method(path, cls_name, name, namespace):
	tree = ast.parse(path.read_text())
	cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls_name)
	fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
	fn.decorator_list = []
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), namespace)
	return namespace[name]


class TestTheFormDoesNotRequireATemplate(unittest.TestCase):
	def field(self):
		doc = json.loads(APPRAISAL_JSON.read_text())
		return next(f for f in doc["fields"] if f["fieldname"] == "appraisal_template")

	def test_the_template_is_never_required(self):
		field = self.field()
		self.assertFalse(field.get("reqd"), "the template is not required")
		self.assertNotIn("mandatory_depends_on", field, "not even once the appraisal is saved")

	def test_the_change_reaches_sites_that_already_have_the_doctype(self):
		# a standard doctype only re-syncs when `modified` moves past the site's copy
		doc = json.loads(APPRAISAL_JSON.read_text())
		self.assertGreaterEqual(doc["modified"], "2026-11-03")


class TestACycleCreatesAppraisalsWithoutATemplate(unittest.TestCase):
	def run_create(self, appraisees):
		frappe = MagicMock()
		frappe.throw.side_effect = _Refused
		frappe.msgprint = MagicMock()
		created = MagicMock()
		ns = {
			"frappe": frappe,
			"_": lambda s: s,
			"create_appraisals_for_cycle": created,
			"logger": MagicMock(),
		}
		create = _method(CYCLE, "AppraisalCycle", "create_appraisals", ns)
		cycle = SimpleNamespace(
			appraisees=appraisees,
			check_permission=MagicMock(),
			show_missing_template_message=MagicMock(side_effect=_Refused),
			reload=MagicMock(),
			name="Cycle 2026",
		)
		create(cycle)
		return created, cycle

	def test_an_employee_with_no_template_does_not_stop_the_batch(self):
		created, cycle = self.run_create(
			[
				SimpleNamespace(employee="E1", appraisal_template="Ops"),
				SimpleNamespace(employee="E2", appraisal_template=None),
			]
		)
		created.assert_called_once()
		cycle.show_missing_template_message.assert_not_called()

	def test_no_employees_is_still_refused(self):
		with self.assertRaises(_Refused):
			self.run_create([])


class TestFeedbackOnAnAppraisalWithNoTemplate(unittest.TestCase):
	def run_criteria(self, template):
		frappe = MagicMock()
		frappe.db.get_value.return_value = template
		frappe.get_doc.return_value = SimpleNamespace(
			rating_criteria=[SimpleNamespace(criteria="Teamwork", per_weightage=100)]
		)
		ns = {"frappe": frappe, "_": lambda s: s, "logger": MagicMock()}
		set_criteria = _method(FEEDBACK, "EmployeePerformanceFeedback", "set_feedback_criteria", ns)
		rows = []
		doc = SimpleNamespace(
			appraisal="APR-1", set=lambda f, v: rows.clear(), append=lambda f, r: rows.append(r)
		)
		set_criteria(doc)
		return frappe, rows

	def test_no_template_means_no_criteria_and_no_crash(self):
		frappe, rows = self.run_criteria(None)
		frappe.get_doc.assert_not_called()
		self.assertEqual(rows, [])

	def test_a_template_still_fills_the_criteria(self):
		_frappe, rows = self.run_criteria("Ops")
		self.assertEqual([r["criteria"] for r in rows], ["Teamwork"])


if __name__ == "__main__":
	unittest.main()

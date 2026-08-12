"""Every Appraisal child table carries a free-text `description` field.

User requirement (2026-08-11): each child doctype of every table inside
Appraisal must let HR record a per-row description. Two tables already had
their own variant and are exempt: Appraisal Demerit (`description`) and
Appraisal Extra Initiative (`description_impact`). The other seven get a
uniform `description` Small Text, kept out of the grid (`in_list_view` unset)
so row detail stays the reading surface.

Pure static check over the repo's JSON — no bench, no site.
"""

import json
import pathlib
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]

CHILD_DOCTYPES = [
	"appraisal_kra",
	"appraisal_goal",
	"appraisal_functional_competency",
	"employee_feedback_rating",
	"appraisal_b4_evidence",
	"appraisal_b5_evidence",
	"leadership_scorecard",
]


def _load(doctype_dir):
	path = HRMS_ROOT / "hr" / "doctype" / doctype_dir / f"{doctype_dir}.json"
	return json.loads(path.read_text(encoding="utf-8"))


class TestAppraisalChildDescriptions(unittest.TestCase):
	def test_description_field_present_and_conformant(self):
		for doctype_dir in CHILD_DOCTYPES:
			with self.subTest(doctype=doctype_dir):
				doc = _load(doctype_dir)
				fields = {f["fieldname"]: f for f in doc["fields"]}
				self.assertIn("description", fields, f"{doctype_dir}: missing description field")
				field = fields["description"]
				self.assertEqual(field["fieldtype"], "Small Text", doctype_dir)
				self.assertEqual(field["label"], "Description", doctype_dir)
				self.assertFalse(field.get("in_list_view"), f"{doctype_dir}: keep grids uncrowded")
				# appraisal_goal is a legacy-format JSON without field_order;
				# there the fields array position alone defines placement
				if "field_order" in doc:
					self.assertIn("description", doc["field_order"], doctype_dir)


if __name__ == "__main__":
	unittest.main()

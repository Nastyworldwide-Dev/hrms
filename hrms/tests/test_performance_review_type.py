"""Performance Review Type on an Appraisal (owner, 13 Nov 2026).

Each Appraisal says what kind of review it is. HR keep the list themselves
(add, rename, retire) in Desk, the way they keep HR Letter Type; it starts with
the five HR named.

    python3 -m pytest -q hrms/tests/test_performance_review_type.py
"""

import json
import pathlib
import unittest
from unittest.mock import patch

HR = pathlib.Path(__file__).resolve().parents[1] / "hr" / "doctype"
STARTING = ("Confirmation Review", "PIP Review", "Performance Review", "Assignment Review", "Others")


def _meta(name):
	return json.loads((HR / name / f"{name}.json").read_text())


class TestTheList(unittest.TestCase):
	def test_hr_can_add_and_edit_review_types(self):
		meta = _meta("performance_review_type")
		perms = {p["role"]: p for p in meta["permissions"]}
		for role in ("HR Manager", "HR User"):
			for right in ("read", "create", "write"):
				self.assertEqual(perms[role].get(right), 1, f"{role} {right}")
		self.assertEqual(meta.get("allow_rename"), 1)

	def test_a_type_can_be_switched_off_without_deleting_it(self):
		fields = {f["fieldname"]: f for f in _meta("performance_review_type")["fields"]}
		self.assertEqual(fields["disabled"]["fieldtype"], "Check")

	def test_it_starts_with_the_five_hr_named(self):
		from hrms.utils import performance_review_type as prt

		self.assertEqual(prt.STARTING_TYPES, STARTING)
		added = []
		with (
			patch.object(
				prt.frappe.db, "exists", side_effect=lambda dt, name: name == "PIP Review", create=True
			),
			patch.object(
				prt.frappe,
				"get_doc",
				side_effect=lambda d: type(
					"D", (), {"insert": lambda self, **k: added.append(d["review_type"])}
				)(),
				create=True,
			),
		):
			prt.seed_review_types()
		self.assertEqual(added, [t for t in STARTING if t != "PIP Review"])


class TestTheAppraisalField(unittest.TestCase):
	def _field(self):
		meta = _meta("appraisal")
		return meta, {f["fieldname"]: f for f in meta["fields"]}.get("performance_review_type")

	def test_appraisal_has_a_performance_review_type_from_the_list(self):
		_, field = self._field()
		self.assertEqual(
			(field["fieldtype"], field["options"], field["label"]),
			("Link", "Performance Review Type", "Performance Review Type"),
		)

	def test_it_sits_beside_the_appraisal_cycle(self):
		meta, _ = self._field()
		order = meta["field_order"]
		self.assertEqual(order.index("performance_review_type"), order.index("appraisal_cycle") + 1)

	def test_old_appraisals_still_save_without_one(self):
		_, field = self._field()
		self.assertFalse(field.get("reqd"))

	def test_a_switched_off_type_is_not_offered(self):
		js = (HR / "appraisal" / "appraisal.js").read_text()
		self.assertIn('set_query("performance_review_type"', js)
		self.assertIn("disabled: 0", js)


class TestItIsSetUpEverywhere(unittest.TestCase):
	def test_a_patch_seeds_existing_sites_and_install_seeds_new_ones(self):
		root = HR.parents[1]
		self.assertIn("hrms.patches.v16_0.add_performance_review_type", (root / "patches.txt").read_text())
		self.assertIn("seed_review_types", (root / "setup.py").read_text())


if __name__ == "__main__":
	unittest.main()


class TestTheCycleType(unittest.TestCase):
	"""Owner, 13 Nov 2026: cycles were only ever quarters (Q1, Q2 2026 - NHSB...).
	A Cycle Type says Monthly, Quarterly, Half Yearly or Yearly, and fills the end
	date from the start date. The dates stay editable."""

	def test_the_cycle_offers_the_four_types(self):
		fields = {f["fieldname"]: f for f in _meta("appraisal_cycle")["fields"]}
		ct = fields["cycle_type"]
		self.assertEqual(ct["fieldtype"], "Select")
		self.assertEqual(ct["options"].split("\n"), ["", "Monthly", "Quarterly", "Half Yearly", "Yearly"])
		self.assertFalse(ct.get("reqd"), "cycles made before keep saving")

	def test_the_end_date_follows_the_type(self):
		import datetime as dt

		from hrms.utils.performance_review_type import cycle_end

		start = dt.date(2026, 1, 1)
		self.assertEqual(cycle_end(start, "Monthly"), dt.date(2026, 1, 31))
		self.assertEqual(cycle_end(start, "Quarterly"), dt.date(2026, 3, 31))
		self.assertEqual(cycle_end(start, "Half Yearly"), dt.date(2026, 6, 30))
		self.assertEqual(cycle_end(start, "Yearly"), dt.date(2026, 12, 31))
		self.assertEqual(cycle_end(dt.date(2026, 2, 1), "Monthly"), dt.date(2026, 2, 28))
		self.assertIsNone(cycle_end(start, ""))

	def test_the_cycle_picker_shows_the_type(self):
		meta = _meta("appraisal_cycle")
		self.assertIn("cycle_type", meta.get("search_fields") or "")

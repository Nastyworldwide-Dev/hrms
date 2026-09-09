"""Location evidence: the fields a punch and its approval request must carry.

Bench-free JSON and source checks. Run as a file:

    PYTHONPATH=. python3 hrms/tests/test_location_evidence.py
"""

import json
import pathlib
import unittest

HRMS = pathlib.Path(__file__).resolve().parent.parent
CHECKIN = HRMS / "hr/doctype/employee_checkin/employee_checkin.json"
REQUEST = HRMS / "hr/doctype/remote_checkin_request/remote_checkin_request.json"
REPORT = HRMS / "hr/report/out_of_radius_activity/out_of_radius_activity.py"

CHECKIN_FIELDS = {
	"location_accuracy_m": "Float",
	"location_fix_age_s": "Int",
	"location_source": "Select",
	"geofence_distance_m": "Float",
	"geofence_radius_m": "Int",
	"geofence_outcome": "Select",
}
REQUEST_FIELDS = {"accuracy_m": "Float", "radius_m": "Int", "reason": "Select"}
OUTCOMES = {
	"Inside",
	"Outside",
	"Imprecise",
	"Free Location",
	"No Shift",
	"No Location",
	"No Radius",
	"Tracking Off",
	"Late Checkout",
	"Manual Entry",
}


def _fields(path):
	return {f["fieldname"]: f for f in json.loads(path.read_text())["fields"]}


class TestCheckinCarriesEvidence(unittest.TestCase):
	def test_fields_exist_read_only_with_the_right_types(self):
		fields = _fields(CHECKIN)
		for name, ftype in CHECKIN_FIELDS.items():
			with self.subTest(field=name):
				self.assertIn(name, fields)
				self.assertEqual(fields[name]["fieldtype"], ftype)
				self.assertEqual(fields[name].get("read_only"), 1, f"{name} is evidence, never typed in")

	def test_outcome_options_cover_every_branch(self):
		options = set(_fields(CHECKIN)["geofence_outcome"]["options"].split("\n")) - {""}
		self.assertEqual(options, OUTCOMES)

	def test_modified_was_bumped(self):
		self.assertGreater(json.loads(CHECKIN.read_text())["modified"], "2026-09-09")


class TestRequestCarriesEvidence(unittest.TestCase):
	def test_fields_exist(self):
		fields = _fields(REQUEST)
		for name, ftype in REQUEST_FIELDS.items():
			with self.subTest(field=name):
				self.assertIn(name, fields)
				self.assertEqual(fields[name]["fieldtype"], ftype)
		self.assertEqual(
			set(fields["reason"]["options"].split("\n")) - {""}, {"Outside Radius", "Imprecise Location"}
		)

	def test_modified_was_bumped(self):
		self.assertGreater(json.loads(REQUEST.read_text())["modified"], "2026-09-09")


class TestReportShowsAccuracy(unittest.TestCase):
	def test_report_has_an_accuracy_column_and_selects_it(self):
		src = REPORT.read_text()
		self.assertIn('"fieldname": "accuracy_m"', src)
		self.assertIn("rcr.accuracy_m", src)


if __name__ == "__main__":
	unittest.main()

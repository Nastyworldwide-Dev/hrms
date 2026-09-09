"""A Shift Location pinned from a Chinese map lands where phones report it.

PYTHONPATH=. python3 hrms/tests/test_shift_location_coordinates.py
"""

import json
import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from hrms.utils.coordinates import BD09, GCJ02, WGS84, gcj02_to_wgs84, to_wgs84, wgs84_to_gcj02

HRMS = pathlib.Path(__file__).resolve().parent.parent
JSON = HRMS / "hr/doctype/shift_location/shift_location.json"

# Beijing, Tiananmen: WGS-84 39.90733, 116.39122 reads as GCJ-02 39.90870, 116.39750 on Chinese maps.
TIANANMEN_WGS = (39.90733, 116.39122)
TIANANMEN_GCJ = (39.90870, 116.39750)


def metres(a, b):
	dlat = math.radians(b[0] - a[0])
	dlng = math.radians(b[1] - a[1])
	x = dlng * math.cos(math.radians((a[0] + b[0]) / 2))
	return math.hypot(dlat, x) * 6371008.8


class TestConversion(unittest.TestCase):
	def test_gcj02_pin_comes_back_to_where_the_phone_stands(self):
		self.assertLess(metres(gcj02_to_wgs84(*TIANANMEN_GCJ), TIANANMEN_WGS), 10)

	def test_the_offset_a_chinese_map_introduces_is_hundreds_of_metres(self):
		self.assertGreater(metres(TIANANMEN_GCJ, TIANANMEN_WGS), 300)

	def test_round_trip_is_metre_accurate(self):
		g = wgs84_to_gcj02(*TIANANMEN_WGS)
		self.assertLess(metres(gcj02_to_wgs84(*g), TIANANMEN_WGS), 2)

	def test_outside_china_nothing_moves(self):
		kl = (3.1390, 101.6869)
		self.assertEqual(to_wgs84(*kl, GCJ02), kl)

	def test_bd09_goes_through_gcj02(self):
		bd = (39.915, 116.404)  # roughly Tiananmen on Baidu
		self.assertLess(metres(to_wgs84(*bd, BD09), TIANANMEN_WGS), 60)

	def test_wgs84_is_identity_and_unknown_systems_refuse(self):
		self.assertEqual(to_wgs84(*TIANANMEN_WGS, WGS84), TIANANMEN_WGS)
		with self.assertRaises(ValueError):
			to_wgs84(1, 2, "Mars")


class TestShiftLocationConverts(unittest.TestCase):
	def test_a_gcj02_pin_is_stored_as_wgs84_and_marked_so(self):
		from types import SimpleNamespace

		from hrms.hr.doctype.shift_location import shift_location as mod

		doc = SimpleNamespace(
			latitude=TIANANMEN_GCJ[0], longitude=TIANANMEN_GCJ[1], coordinate_system=GCJ02, name="CN Office"
		)
		mod.ShiftLocation.convert_coordinates(doc)
		self.assertLess(metres((doc.latitude, doc.longitude), TIANANMEN_WGS), 10)
		self.assertEqual(doc.coordinate_system, WGS84, "stored once, as the phones see it")

	def test_a_wgs84_pin_is_untouched(self):
		from types import SimpleNamespace

		from hrms.hr.doctype.shift_location import shift_location as mod

		doc = SimpleNamespace(latitude=3.1390, longitude=101.6869, coordinate_system=WGS84, name="KL")
		mod.ShiftLocation.convert_coordinates(doc)
		self.assertEqual((doc.latitude, doc.longitude), (3.1390, 101.6869))


class TestShiftLocationRefusesAnUnknownMap(unittest.TestCase):
	def test_an_unknown_system_is_a_validation_error_not_a_traceback(self):
		from types import SimpleNamespace

		import frappe

		from hrms.hr.doctype.shift_location import shift_location as mod

		doc = SimpleNamespace(latitude=39.9, longitude=116.4, coordinate_system="Mars", name="X")
		with self.assertRaises(frappe.ValidationError):
			mod.ShiftLocation.convert_coordinates(doc)

	def test_the_form_resets_the_map_choice_when_fetching_a_live_fix(self):
		js = (HRMS / "hr/doctype/shift_location/shift_location.js").read_text()
		fetch = js[js.index("fetch_geolocation: (frm)") :]
		self.assertIn('frm.set_value("coordinate_system", "WGS-84")', fetch.split("},")[0])


class TestShiftLocationSchema(unittest.TestCase):
	def test_the_form_asks_which_map_the_pin_came_from(self):
		fields = {f["fieldname"]: f for f in json.loads(JSON.read_text())["fields"]}
		f = fields["coordinate_system"]
		self.assertEqual(f["fieldtype"], "Select")
		self.assertEqual(set(f["options"].split("\n")) - {""}, {WGS84, GCJ02, BD09})
		self.assertEqual(f.get("default"), WGS84)
		self.assertIn("china", f.get("description", "").lower())
		self.assertGreater(json.loads(JSON.read_text())["modified"], "2026-09-09 04")


if __name__ == "__main__":
	unittest.main()

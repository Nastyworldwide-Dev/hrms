"""Check in at more than one site (HR, 28 Sep 2026).

HR ticks "Can check in at more than one site" on an employee and picks other
sites. Inside ANY of them is accepted and the site is recorded; outside all of
them follows today's rule, measured against the nearest site. Not ticked is
exactly today. Pure — no bench.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_geofence_multi_site.py
"""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from hrms.utils.geofence import evaluate_geofence, evaluate_sites

# Two sites ~5.5 km apart on the same parallel, 100 m radius each.
DAMANSARA = {"name": "Damansara", "latitude": 3.1500, "longitude": 101.6200, "checkin_radius": 100}
SHAH_ALAM = {"name": "Shah Alam", "latitude": 3.1500, "longitude": 101.6700, "checkin_radius": 100}
AT_DAMANSARA = (3.1500, 101.6201)
AT_SHAH_ALAM = (3.1500, 101.6701)
FAR = (3.3000, 101.9000)


def run(point, sites, strict=False, accuracy=None):
	return evaluate_sites(
		strict=strict, sites=sites, latitude=point[0], longitude=point[1], accuracy_m=accuracy
	)


class TestAnySiteAccepts(unittest.TestCase):
	def test_the_second_site_accepts(self):
		matched, decision, _ = run(AT_SHAH_ALAM, [DAMANSARA, SHAH_ALAM])
		self.assertIsNone(decision)
		self.assertEqual(matched, "Shah Alam")

	def test_the_main_site_still_accepts(self):
		matched, decision, _ = run(AT_DAMANSARA, [DAMANSARA, SHAH_ALAM])
		self.assertIsNone(decision)
		self.assertEqual(matched, "Damansara")

	def test_strict_accepts_either_site_too(self):
		matched, decision, _ = run(AT_SHAH_ALAM, [DAMANSARA, SHAH_ALAM], strict=True)
		self.assertIsNone(decision)
		self.assertEqual(matched, "Shah Alam")


class TestOutsideAll(unittest.TestCase):
	def test_lenient_goes_to_the_approver_naming_the_nearest_site(self):
		near_shah_alam = (3.1500, 101.6800)
		matched, decision, nearest = run(near_shah_alam, [DAMANSARA, SHAH_ALAM])
		self.assertIsNone(matched)
		self.assertEqual(decision[0], "require_remote")
		self.assertEqual(nearest["name"], "Shah Alam")
		self.assertLess(decision[1]["distance_m"], 2000, "measured from the nearest, not the main site")

	def test_strict_refuses(self):
		matched, decision, _ = run(FAR, [DAMANSARA, SHAH_ALAM], strict=True)
		self.assertIsNone(matched)
		self.assertEqual(decision[0], "throw")


class TestOneSiteIsToday(unittest.TestCase):
	"""Not ticked = one site = the same answer evaluate_geofence gives today."""

	def _today(self, point, strict=False):
		from hrms.utils.geofence import distance_to

		return evaluate_geofence(
			strict=strict,
			has_shift_location=True,
			radius_m=DAMANSARA["checkin_radius"],
			distance_m=distance_to(DAMANSARA, *point),
		)

	def test_inside_matches_today(self):
		matched, decision, _ = run(AT_DAMANSARA, [DAMANSARA])
		self.assertEqual(decision, self._today(AT_DAMANSARA))
		self.assertEqual(matched, "Damansara")

	def test_outside_matches_today(self):
		for strict in (False, True):
			_, decision, _ = run(FAR, [DAMANSARA], strict=strict)
			self.assertEqual(decision, self._today(FAR, strict), f"strict={strict}")

	def test_no_site_matches_today(self):
		for strict in (False, True):
			_, decision, _ = run(FAR, [], strict=strict)
			self.assertEqual(
				decision,
				evaluate_geofence(strict=strict, has_shift_location=False, radius_m=0, distance_m=None),
				f"strict={strict}",
			)


class TestFreeLocation(unittest.TestCase):
	def test_a_free_site_among_several_accepts_anywhere(self):
		free = dict(SHAH_ALAM, is_free_location=1)
		matched, decision, _ = run(FAR, [DAMANSARA, free])
		self.assertIsNone(decision)
		self.assertEqual(matched, "Shah Alam")


class TestSiteList(unittest.TestCase):
	def test_ticked_adds_other_sites_after_the_main_one(self):
		from hrms.utils.geofence import site_names

		self.assertEqual(
			site_names("Damansara", True, ["Shah Alam", "Damansara", "Klang"]),
			["Damansara", "Shah Alam", "Klang"],
		)

	def test_not_ticked_ignores_other_sites(self):
		from hrms.utils.geofence import site_names

		self.assertEqual(site_names("Damansara", False, ["Shah Alam"]), ["Damansara"])

	def test_no_main_site_but_ticked_uses_the_others(self):
		from hrms.utils.geofence import site_names

		self.assertEqual(site_names(None, True, ["Shah Alam"]), ["Shah Alam"])

	def test_nothing_at_all(self):
		from hrms.utils.geofence import site_names

		self.assertEqual(site_names(None, False, []), [])


if __name__ == "__main__":
	unittest.main()


class TestShiftRulesNeverReadOtherSites(unittest.TestCase):
	"""Owner, 28 Sep 2026: the other sites are for check-ins only. The automatic
	shift rules run from Employee.shift_location, and must never start reading
	the multi-site fields — a second site would then change people's shifts."""

	def test_the_shift_rules_module_does_not_mention_them(self):
		source = (pathlib.Path(__file__).resolve().parents[1] / "hr/shift_rules.py").read_text()
		for name in ("multi_site_checkin", "other_checkin_sites", "Employee Other Site", "employee_sites"):
			self.assertNotIn(name, source, name)

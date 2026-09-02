"""Unit tests for hrms.utils.geofence.evaluate_geofence.

Pure-logic tests covering the Strict Shift Location Check-in matrix.
Run with:
    python3 -m unittest hrms.utils.test_geofence
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from hrms.utils.geofence import (
	ACCURACY_ALLOWANCE_CAP_M,
	REASON_IMPRECISE_LOCATION,
	REASON_NO_RADIUS,
	REASON_NO_SHIFT_LOCATION,
	REASON_OUTSIDE_RADIUS,
	evaluate_geofence,
)


class TestEvaluateGeofence(unittest.TestCase):
	# --- Lenient mode (default behaviour) ---

	def test_lenient_no_shift_location_allows(self):
		self.assertIsNone(evaluate_geofence(False, has_shift_location=False, radius_m=100, distance_m=50))

	def test_lenient_zero_radius_allows(self):
		self.assertIsNone(evaluate_geofence(False, has_shift_location=True, radius_m=0, distance_m=999))

	def test_lenient_negative_radius_allows(self):
		self.assertIsNone(evaluate_geofence(False, has_shift_location=True, radius_m=-5, distance_m=999))

	def test_lenient_inside_radius_allows(self):
		self.assertIsNone(evaluate_geofence(False, has_shift_location=True, radius_m=100, distance_m=80))

	def test_lenient_on_boundary_allows(self):
		# distance == radius is considered inside (<=)
		self.assertIsNone(evaluate_geofence(False, has_shift_location=True, radius_m=100, distance_m=100))

	def test_lenient_outside_radius_requires_remote(self):
		action, ctx = evaluate_geofence(False, has_shift_location=True, radius_m=100, distance_m=250)
		self.assertEqual(action, "require_remote")
		self.assertEqual(ctx["reason"], REASON_OUTSIDE_RADIUS)
		self.assertEqual(ctx["distance_m"], 250)
		self.assertEqual(ctx["radius_m"], 100)
		self.assertEqual(ctx["overshoot_m"], 150)

	# --- Strict mode ---

	def test_strict_no_shift_location_throws(self):
		action, ctx = evaluate_geofence(True, has_shift_location=False, radius_m=100, distance_m=50)
		self.assertEqual(action, "throw")
		self.assertEqual(ctx["reason"], REASON_NO_SHIFT_LOCATION)

	def test_strict_zero_radius_throws(self):
		action, ctx = evaluate_geofence(True, has_shift_location=True, radius_m=0, distance_m=10)
		self.assertEqual(action, "throw")
		self.assertEqual(ctx["reason"], REASON_NO_RADIUS)

	def test_strict_negative_radius_throws(self):
		action, ctx = evaluate_geofence(True, has_shift_location=True, radius_m=-1, distance_m=10)
		self.assertEqual(action, "throw")
		self.assertEqual(ctx["reason"], REASON_NO_RADIUS)

	def test_strict_inside_radius_allows(self):
		self.assertIsNone(evaluate_geofence(True, has_shift_location=True, radius_m=100, distance_m=80))

	def test_strict_on_boundary_allows(self):
		self.assertIsNone(evaluate_geofence(True, has_shift_location=True, radius_m=100, distance_m=100))

	def test_strict_outside_radius_throws_with_context(self):
		action, ctx = evaluate_geofence(True, has_shift_location=True, radius_m=100, distance_m=250)
		self.assertEqual(action, "throw")
		self.assertEqual(ctx["reason"], REASON_OUTSIDE_RADIUS)
		self.assertEqual(ctx["distance_m"], 250)
		self.assertEqual(ctx["radius_m"], 100)
		self.assertEqual(ctx["overshoot_m"], 150)

	# --- Defensive: missing distance ---

	def test_strict_missing_distance_throws_outside(self):
		action, ctx = evaluate_geofence(True, has_shift_location=True, radius_m=100, distance_m=None)
		self.assertEqual(action, "throw")
		self.assertEqual(ctx["reason"], REASON_OUTSIDE_RADIUS)

	def test_lenient_missing_distance_routes_to_remote(self):
		action, ctx = evaluate_geofence(False, has_shift_location=True, radius_m=100, distance_m=None)
		self.assertEqual(action, "require_remote")
		self.assertEqual(ctx["reason"], REASON_OUTSIDE_RADIUS)


class TestAccuracyAllowance(unittest.TestCase):
	"""The device's own error estimate is part of the reading.

	A 100 m fence and a handset that says "somewhere within 40 m of here" do
	not disagree when the reported point is 120 m out — the employee can be
	standing on the doorstep and produce exactly that. Before the allowance
	existed, that punch was flagged for a manager to approve, every morning,
	for every employee whose phone was indoors.
	"""

	def test_reading_inside_its_own_error_bar_is_allowed(self):
		# 120 m out, +/-40 m: the doorstep is inside the error bar. Was
		# require_remote (lenient) and a hard block (strict) before.
		self.assertIsNone(
			evaluate_geofence(False, has_shift_location=True, radius_m=100, distance_m=120, accuracy_m=40)
		)
		self.assertIsNone(
			evaluate_geofence(True, has_shift_location=True, radius_m=100, distance_m=120, accuracy_m=40)
		)

	def test_allowance_does_not_excuse_a_genuine_miss(self):
		action, ctx = evaluate_geofence(
			False, has_shift_location=True, radius_m=100, distance_m=500, accuracy_m=40
		)
		self.assertEqual(action, "require_remote")
		self.assertEqual(ctx["reason"], REASON_OUTSIDE_RADIUS)
		# overshoot stays the raw distance-over-radius; the slack is reported
		# separately so an approver can see how firm the number is.
		self.assertEqual(ctx["overshoot_m"], 400)
		self.assertEqual(ctx["accuracy_m"], 40)

	def test_boundary_of_the_allowance_is_inside(self):
		self.assertIsNone(
			evaluate_geofence(True, has_shift_location=True, radius_m=100, distance_m=140, accuracy_m=40)
		)

	def test_unknown_accuracy_behaves_exactly_as_before(self):
		# Biometric device punches and Desk-entered rows carry no accuracy.
		# They must keep the pre-allowance decision, not be handed free slack.
		action, ctx = evaluate_geofence(
			False, has_shift_location=True, radius_m=100, distance_m=120, accuracy_m=None
		)
		self.assertEqual(action, "require_remote")
		self.assertEqual(ctx["accuracy_m"], 0.0)

	# --- Readings too coarse to place anyone ---

	def test_coarse_reading_throws_under_strict(self):
		# A wired desktop geolocates by IP and reports kilometres.
		action, ctx = evaluate_geofence(
			True, has_shift_location=True, radius_m=100, distance_m=3000, accuracy_m=5000
		)
		self.assertEqual(action, "throw")
		self.assertEqual(ctx["reason"], REASON_IMPRECISE_LOCATION)
		self.assertEqual(ctx["accuracy_m"], 5000)

	def test_coarse_reading_routes_to_a_human_under_lenient(self):
		action, ctx = evaluate_geofence(
			False, has_shift_location=True, radius_m=100, distance_m=3000, accuracy_m=5000
		)
		self.assertEqual(action, "require_remote")
		self.assertEqual(ctx["reason"], REASON_IMPRECISE_LOCATION)

	def test_coarse_reading_cannot_buy_its_way_inside(self):
		# The direction that gets abused: a city-centre IP fix lands "inside"
		# a nearby site's fence by luck. Being unplaceable is not presence.
		action, ctx = evaluate_geofence(
			False, has_shift_location=True, radius_m=100, distance_m=10, accuracy_m=5000
		)
		self.assertEqual(action, "require_remote")
		self.assertEqual(ctx["reason"], REASON_IMPRECISE_LOCATION)

	def test_cap_itself_still_buys_allowance(self):
		self.assertIsNone(
			evaluate_geofence(
				True,
				has_shift_location=True,
				radius_m=100,
				distance_m=100 + ACCURACY_ALLOWANCE_CAP_M,
				accuracy_m=ACCURACY_ALLOWANCE_CAP_M,
			)
		)

	def test_misconfiguration_is_reported_before_imprecision(self):
		# An admin who never set a Shift Location must hear about that, not
		# about the employee's wifi.
		_action, ctx = evaluate_geofence(
			True, has_shift_location=False, radius_m=100, distance_m=10, accuracy_m=9000
		)
		self.assertEqual(ctx["reason"], REASON_NO_SHIFT_LOCATION)

	# --- Values arriving off an HTTP request ---

	def test_accuracy_arrives_as_a_string(self):
		self.assertIsNone(
			evaluate_geofence(True, has_shift_location=True, radius_m=100, distance_m=120, accuracy_m="40")
		)

	def test_junk_accuracy_buys_nothing_and_does_not_crash(self):
		for junk in ("", "abc", object(), -50):
			with self.subTest(junk=junk):
				action, ctx = evaluate_geofence(
					False, has_shift_location=True, radius_m=100, distance_m=120, accuracy_m=junk
				)
				self.assertEqual(action, "require_remote")
				self.assertEqual(ctx["reason"], REASON_OUTSIDE_RADIUS)
				self.assertEqual(ctx["accuracy_m"], 0.0)


class TestEffectiveShiftLocation(unittest.TestCase):
	"""The fence resolves off the active assignment's shift_location, but only
	rule-created assignments carry one — a manual/schedule assignment does not,
	so a configured Employee.shift_location (Damansara, reproduced live) resolved
	to "no area set". effective_shift_location must fall back to the Employee.
	"""

	def test_no_assignment_falls_back_to_employee(self):
		from hrms.utils.geofence import effective_shift_location

		# No active shift today, but Employee.shift_location is set: the employee
		# field is the authoritative "where they clock in", so the area still
		# resolves. Live evidence (Employee linked to Damansara, no active
		# assignment) showed "no area set" was wrong here.
		with patch("frappe.db.get_value", return_value="Damansara") as gv:
			self.assertEqual(effective_shift_location("EMP-1", None), "Damansara")
			gv.assert_called_once_with("Employee", "EMP-1", "shift_location")

	def test_no_assignment_and_no_employee_location_returns_none(self):
		from hrms.utils.geofence import effective_shift_location

		with patch("frappe.db.get_value", return_value=None):
			self.assertIsNone(effective_shift_location("EMP-1", None))

	def test_assignment_with_location_wins_without_touching_employee(self):
		from hrms.utils.geofence import effective_shift_location

		assignment = SimpleNamespace(shift_location="Damansara")
		with patch("frappe.db.get_value") as gv:
			result = effective_shift_location("EMP-1", assignment)
			gv.assert_not_called()
		self.assertEqual(result, "Damansara")

	def test_assignment_without_location_falls_back_to_employee(self):
		from hrms.utils.geofence import effective_shift_location

		assignment = SimpleNamespace(shift_location=None)
		with patch("frappe.db.get_value", return_value="Damansara") as gv:
			result = effective_shift_location("EMP-1", assignment)
			gv.assert_called_once_with("Employee", "EMP-1", "shift_location")
		self.assertEqual(result, "Damansara")

	def test_no_location_anywhere_returns_none(self):
		from hrms.utils.geofence import effective_shift_location

		assignment = SimpleNamespace(shift_location=None)
		with patch("frappe.db.get_value", return_value=None):
			self.assertIsNone(effective_shift_location("EMP-1", assignment))


if __name__ == "__main__":
	unittest.main()

"""Unit tests for nsty.utils.geofence.evaluate_geofence.

Pure-logic tests covering the Strict Shift Location Check-in matrix.
Run with:
    python3 -m unittest nsty.utils.test_geofence
"""

import unittest

from nsty.utils.geofence import (
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


if __name__ == "__main__":
	unittest.main()

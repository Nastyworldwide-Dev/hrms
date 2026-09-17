"""One metre of extra reported error must not cost 250 metres of tolerance.

Owner, 17 Sep 2026: "i still get report regarding geofence, some experience had
to remote request despite in the area for check in. accuracy problems."

Measured on the real function before the fix — same person, same spot, 80 m
from the centre of a 50 m fence:

    accuracy 249 m -> ALLOWED
    accuracy 250 m -> ALLOWED
    accuracy 251 m -> require_remote (imprecise_location)

The allowance was `accuracy` up to the 250 m cap and then ZERO, so a reading
one metre coarser than the cap lost the whole allowance at once. Between the
allowance cap and the point-estimate trust cap the code already treats the
device's own estimate as meaningful — it says so, and it allows a point that
lands inside — but it gave that same estimate no tolerance at all the moment
the point landed a few metres outside. Trusted when it helps, discarded when
it does not: a phone indoors reading 400 m of error sent someone at their desk
to their approver.

The allowance is now `min(accuracy, 250)` for every reading the code trusts at
all, so it never decreases as the reading gets worse. Past the trust cap
nothing changes: an IP-level fix places nobody, and landing inside a fence by
a provider's centroid is luck, not presence.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_geofence_allowance_has_no_cliff.py
"""

from __future__ import annotations

import unittest

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.utils.geofence import (
	ACCURACY_ALLOWANCE_CAP_M,
	POINT_ESTIMATE_TRUST_CAP_M,
	REASON_IMPRECISE_LOCATION,
	REASON_OUTSIDE_RADIUS,
	evaluate_geofence,
)

RADIUS = 50


def verdict(distance, accuracy, strict=False):
	return evaluate_geofence(strict, True, RADIUS, distance, accuracy)


class NoCliffCase(unittest.TestCase):
	def test_one_metre_of_extra_error_does_not_flip_the_answer(self):
		"""The reported case, at the exact metre where it used to flip."""
		at_the_cap = verdict(80, ACCURACY_ALLOWANCE_CAP_M)
		one_worse = verdict(80, ACCURACY_ALLOWANCE_CAP_M + 1)
		self.assertIsNone(at_the_cap)
		self.assertIsNone(one_worse, "a metre more error cannot cost 250 m of tolerance")

	def test_the_allowance_never_shrinks_as_the_reading_gets_worse(self):
		"""Monotonic: a worse reading may buy no more tolerance, but never less.

		A very sharp reading saying 80 m from a 50 m fence means the person IS
		outside, and is refused — correctly. What must never happen is that
		refusal coming BACK once a coarser reading has already been accepted.
		"""
		seen_allowed = False
		for accuracy in range(0, POINT_ESTIMATE_TRUST_CAP_M + 1, 17):
			allowed = verdict(80, accuracy) is None
			if allowed:
				seen_allowed = True
			elif seen_allowed:
				self.fail(
					f"accuracy {accuracy} m is refused after a sharper reading was allowed — "
					"the allowance went backwards"
				)

	def test_a_coarse_reading_still_buys_only_the_capped_allowance(self):
		"""It must not become "any error widens the fence by that much"."""
		self.assertIsNone(verdict(RADIUS + ACCURACY_ALLOWANCE_CAP_M, 1500))
		outside = verdict(RADIUS + ACCURACY_ALLOWANCE_CAP_M + 1, 1500)
		self.assertIsNotNone(outside, "a kilometre of error may not widen the fence by a kilometre")


class WhatMustNotChangeCase(unittest.TestCase):
	def test_a_sharp_reading_well_outside_is_still_outside(self):
		action, context = verdict(900, 10)
		self.assertEqual(action, "require_remote")
		self.assertEqual(context["reason"], REASON_OUTSIDE_RADIUS)

	def test_a_reading_past_the_trust_cap_places_nobody_even_inside_it(self):
		"""An IP-level fix landing inside a fence is luck, not presence."""
		action, context = verdict(10, POINT_ESTIMATE_TRUST_CAP_M + 1)
		self.assertEqual(action, "require_remote")
		self.assertEqual(context["reason"], REASON_IMPRECISE_LOCATION)

	def test_strict_mode_still_throws_where_lenient_routes(self):
		self.assertEqual(verdict(900, 10, strict=True)[0], "throw")
		self.assertEqual(verdict(10, POINT_ESTIMATE_TRUST_CAP_M + 1, strict=True)[0], "throw")

	def test_an_unknown_accuracy_still_buys_nothing(self):
		"""A device that reports no error estimate is measured as a point."""
		self.assertIsNone(verdict(RADIUS, None))
		self.assertIsNotNone(verdict(RADIUS + 1, None))


if __name__ == "__main__":
	unittest.main()

# FAMILY — an allowance that falls to zero one metre past its cap

CLASS: a tolerance expressed as "up to X, then nothing", where the step lands
exactly where the measurements are noisiest. The geofence allowance was
`accuracy` up to 250 m and ZERO beyond it, so the same person, standing in the
same place 80 m from the centre of a 50 m fence, was allowed at 250 m of
reported error and sent to remote approval at 251 m.

Measured on the real function before the fix, not inferred.

ROOT CAUSE: between the allowance cap and the point-estimate trust cap the code
already treats the device's estimate as meaningful — it allows a point that
lands inside — but gave that same estimate no tolerance when the point landed
just outside. Trusted when it helps, discarded when it does not. The allowance
is now `min(accuracy, 250)` for every reading the code trusts at all, so it
never decreases as the reading gets worse and never exceeds the cap.

## Both sides of the same rule, and everything that reads it

hrms/utils/geofence.py:155 (`evaluate_geofence`) — same-root (fixed here)
  The authority. Every punch is decided here.
frontend/src/utils/geolocation.js:124 (`previewGeofence`) — same-root (fixed here)
  The phone's preview of that decision. It must agree case for case, and
  `hrms/tests/test_geolocation_properties.py::TestPreviewParity` failed the
  moment the server changed — which is the test doing exactly its job.
hrms/api/geofence.py (`check_geofence`) — not-affected
  The pre-flight endpoint; it calls `evaluate_geofence` and inherits the fix.
hrms/overrides/employee_checkin_override.py
  (`validate_distance_from_shift_location`) — not-affected
  The enforcement point; also calls `evaluate_geofence`.
hrms/utils/geofence.py::usable_accuracy — not-affected
  Parses the number. An unreadable or absent accuracy is still "unknown" and
  still buys nothing — a device that reports no error estimate is measured as
  a surveyed point, as before.
hrms/utils/geofence.py::POINT_ESTIMATE_TRUST_CAP_M — not-affected
  Unchanged at 2000 m, and still the line past which a reading places nobody.

## The test that pinned the old policy

hrms/utils/test_geofence.py::test_a_coarse_reading_whose_point_is_outside_still_cannot_clear_the_fence
  — same-root (amended here, not deleted)
  It asserted that a coarse reading whose point lands outside buys NOTHING,
  which IS the cliff, written down as expected behaviour. Amended to the new
  rule and renamed: a trusted reading buys the capped allowance and no more —
  50 m outside a fence with 600 m of error is allowed, 300 m outside is not.

## The two real callers, with the line numbers the scan asked for

hrms/api/geofence.py:152 — same-root (fixed here)
  The PWA's pre-flight. It calls `evaluate_geofence` and inherits the corrected
  allowance, which is what stops the sheet warning somebody that it is about to
  send them to an approver they do not need.
hrms/overrides/employee_checkin_override.py:605 — same-root (fixed here)
  The enforcement point on every punch. Same call, same inheritance. Neither
  caller needed a change of its own: the rule lives in one function on purpose,
  and that is why fixing it once fixed both.

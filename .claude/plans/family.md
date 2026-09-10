CLASS: a shift stamp written field-by-field, omitting a field of the stamp.
The omitted field here is `overtime_type`; its loss is silent because the
hourly job reads the day's overtime type from the FIRST eligible punch
(hrms/hr/doctype/shift_type/shift_type.py:452), so one unstamped punch
deletes the whole day's overtime with no error and no log.

Call sites (machine-listed writers of shift_actual_start / the stamp):

- hrms/overrides/employee_checkin_override.py:111 (multi-assignment branch)
  same-root — now calls _stamp_shift
- hrms/overrides/employee_checkin_override.py:142 (_attach_early_arrival)
  same-root — now calls _stamp_shift; this is the reported instance
- hrms/overrides/employee_checkin_override.py:183 (_close_open_session)
  same-root — now calls _stamp_shift, and reads overtime_type off the IN
- hrms/overrides/remote_checkin_request_hooks.py:579 (late-checkout rebind)
  same-root — raw db.set_value, cannot use _stamp_shift; the field tuple now
  carries overtime_type, pinned by an AST test
- hrms/hr/doctype/employee_checkin/employee_checkin.py:94 (upstream fetch_shift)
  not-affected — upstream already sets overtime_type (:101); it is the
  reference the four above were supposed to match
- hrms/hr/doctype/shift_assignment/shift_assignment.py:664 (get_actual_start_end...)
  not-affected — computes timings, never writes a checkin row; it is the
  supplier of overtime_type (:288, :628)
- hrms/sync/runner.py (mirror upsert)
  not-affected — copies whole rows field-for-field, no hand-written stamp
- hrms/hr/report/shift_attendance/shift_attendance.py:235, hrms/utils/ot_calculation.py:366
  not-affected — readers

Class locked by:
- regression: hrms/tests/test_checkin_day_end_to_end.py::
  test_the_overtime_type_survives_an_early_arrival (red on HEAD:
  "None != 'T2E Probe OT Type'")
- invariant: hrms/tests/test_checkin_shift_stamp.py — no resolution path may
  assign a stamp field by hand, and the stamp set is asserted whole, so the
  next field added to it cannot be missed on three paths again.

---

FOLLOW-UP (review of 894e758d0), same CLASS, opposite direction: the fallback
I added resolved `assignment.overtime_type or shift_type.overtime_type`, but
upstream's get_shift_for_time (shift_assignment.py:288) overwrites the shift
type's value with `assignment.overtime_type or None` unconditionally — the
assignment is authoritative, not preferred. So an early punch resolved a type
an on-time punch did not, and pay became a function of arrival time.

- employee_checkin_override.py:636 (_resolve_timings_fallback) — same-root, fixed
- employee_checkin_override.py:181 (_attach_early_arrival second fallback) — same-root, fixed
- employee_checkin_override.py:106 (off-shift branch) — same-root: cleared the
  stamp whole via _clear_shift instead of leaving a stale overtime type
- hr/doctype/employee_checkin/employee_checkin.py:94 (base fetch_shift, the
  fifth writer) — not-affected, it is the reference; now pinned by an AST test
  so a field dropped there is caught

Locked by: test_arrival_time_never_decides_the_overtime_type (red on
894e758d0: "None != 'T2E Probe OT Type'") and
test_the_rebound_out_inherits_the_ins_overtime_type (red on 0cc503069:
"None != 'OT-DAY'") — the first behavioural test of the late-checkout rebind.

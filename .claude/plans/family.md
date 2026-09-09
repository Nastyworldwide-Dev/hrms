# family.md — pending punches auto-marked Absent / Half Day (9 Sep, live)

CLASS: ONE EVIDENCE RULE APPLIED TO TWO QUESTIONS. Overtime asks "which
minutes are verified enough to PAY"; attendance asks "was the person at work".
ae0028f30 (8 Sep) made the hourly job answer the second question with the
first rule (`_is_eligible_checkin`: a pending punch is not evidence), so a
check-in waiting for its approver — the geofence-drift population — produced
no attendance and the absent-marker wrote a submitted Absent; a pending punch
inside a First/Last span split the span into Half Day hours.

Changed: hrms/hr/doctype/shift_type/shift_type.py — new `counts_for_attendance`
(pending counts; rejected/off-shift/skipped do not) used by
`mark_attendance_for_shift_logs` and `get_attendance` on normal days.

Call sites / importers of what changed, with verdicts:
- ShiftType._process → mark_attendance_for_shift_logs (hourly job) — same-root, fixed here.
- ShiftType.get_attendance — same-root, fixed here (segments keyed on counts_for_attendance).
- hrms/overrides/remote_checkin_request_hooks.py reprocess_late_checkout_attendance
  → mark_attendance_for_shift_logs(repair_attendance=…) — same-root: an approved
  late OUT day is rebuilt with the same rule; it already requires the OUT to be
  Approved, so a pending OUT never reaches it.
- hrms/utils/ot_calculation.py _pair_sessions / _is_eligible_checkin (overtime
  discovery, claim capacity, day summary) — not-affected: overtime keeps the
  strict rule on purpose (test_pending_punch_attendance pins it).
- get_attendance holiday branch (`_classify_day != "normal"`) — not-affected:
  still requires an eligible pair; a pending pair on a holiday leaves the day
  unmarked, and mark_absent skips holidays, so no Absent is written.
- ShiftType.mark_absent_for_dates_with_no_attendance — same-root by effect: it
  only ever wrote the Absent because the marker above returned None; with the
  day marked it has nothing to do. Existing provisional Absents are replaced by
  `_replace_provisional_absence` on the next hourly run (their punches were
  never linked, so they are re-read).
- hrms/overrides/remote_checkin_request_hooks.py propagate_approval_decision
  (Rejected → skip_auto_attendance=1) — not-affected: rejection still removes
  the punch from evidence. OPEN (not this fix): a day already marked Present
  from a punch that is later rejected is not rebuilt — the pre-8-Sep state;
  ticket: rebuild the day on rejection under the financial guard.
- hrms/tests/test_ot_nonworking_hours.py harness — same-root: compiles the
  class body with its own namespace; now includes the helper.

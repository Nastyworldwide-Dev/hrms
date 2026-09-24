CLASS: "today's shift" read from Shift Assignment only, ignoring Employee.default_shift (HRMS's own fallback, get_employee_shift consider_default_shift=True)

Instance: Home said "No shift today" while Profile said "Your shift: 9AM - 6PM" (owner screenshot, 24 Sep 2026).

Readers of a day's shift:
- hrms/api/now.py:_shift_window — same-root (fixed: assignment, else default_shift_on)
- hrms/api/calendar.py:_day_shift — same-root (fixed: attendance, check-ins, roster, then default_shift_on)
- hrms/api/team.py:261 — not-affected: already `(att and att.shift) or member.default_shift`
- hrms/api/geofence.py:131,199 — not-affected: the geofence POLICY lives on the assignment row (location, strict flag); a default shift carries no geofence, and the check-in path resolves it separately
- hrms/overrides/employee_checkin_override.py:592 — not-affected: same geofence-policy lookup, narrowed to the punch's resolved shift
- frontend/src/views/Profile.vue:321 — not-affected: reads default_shift (the correct half of the disagreement)

Rest days: a default shift never makes a holiday or weekly off a workday (default_shift_on checks the employee's holiday list); an assignment on a rest day still counts.

Locked: hrms/api/test_now_default_shift.py (5), hrms/api/test_calendar_day_shift.py (+2).

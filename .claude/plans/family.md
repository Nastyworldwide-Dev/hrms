# Family — fix(checkin): a second IN within ten minutes is a duplicate tap, not a check-out (21 Sep 2026)
CLASS: the tap-time session rule coerced ANY IN inside an open session into an OUT; only the 45-second burst window protected against a repeat — a 60-second double tap became a one-minute session
Changed symbols: remote_checkin.resolve_punch_type, is_burst_tap (log_type-aware), DUPLICATE_TAP_WINDOW (new, 10 min = attendance_recovery.DUPLICATE_TAP_MINUTES).
hrms/api/remote_checkin.py:punch same-root — the one caller of both; passes the requested type
hrms/utils/attendance_recovery.py:DUPLICATE_TAP_MINUTES not-affected — the recovery's own 10-minute detector; now the same width at tap time (ticket: one constant, day_rules)
BURST_WINDOW (45 s) kept — a different kind (any-type stutter, e.g. IN/OUT/IN); folding it into 10 min would swallow a real second OUT (pairing table row 6)
Frontend CheckInPanel.vue not-affected — sends the requested type as before; the replay id covers the lost-answer retry

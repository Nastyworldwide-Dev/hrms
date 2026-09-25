CLASS: two different answers to "is this check-in still the session" (phone 16 h, Home 16 h, server 06:00; small-hours tap stored as asked)
frontend/src/components/CheckInPanel.vue isSessionStale — same-root (fixed: utils/checkinSession.js, the server's rule)
hrms/api/now.py _open_session — same-root (fixed: session_open_until)
hrms/api/remote_checkin.py resolve_punch_type band + _session_is_live + get_unresolved_stale_in — same-root (one session_open_until; a tap 00:00-06:00 with no new shift window ends the open day)
hrms/utils/checkin_sweeper.py 36 h — not-affected — flags abandonment long after any session ends; a different question
hrms/utils/ot_calculation.py pairing — not-affected — pairs stored punches; now receives the OUT instead of a second IN

# Family — feat(attendance): Fix days — one press re-stamps, re-pairs and rebuilds a range (21 Sep 2026)
CLASS: HR could correct punches day by day but nothing recomputed the rows they were linked to; HR-owned Absent rows and duplicates survived beside corrected punches, and the glitch left IN and OUT of one day on two shifts
New: hrms/api/attendance_fix_days.py (range loop, preview, per-day refuse/re-stamp/plan/cancel/rebuild/log); attendance_fix_day.fix_days delegate + seams (_range_taps, _roster_stamp, _remark_later), undo reads after_state; restamp.resolved_stamp factored out; day_plan drops burst noise before choosing the closer.
hrms/api/attendance_fix_day.py:rebuild_day same-root — per-day primitive reused; undo now sees its own cancels (latent bug: _log_entry never read after_state)
hrms/utils/restamp.py:restamp same-root — loop body now resolved_stamp(); roster mode of fix_days reuses it
hrms/utils/attendance_recovery.py:session_days same-root — the IN-anchored walk used for day assignment
hrms/utils/attendance_recovery.py:release_to_automation same-root — its exclusion list is the cancel rule (HR-owned rows included when HR asks)
hrms/api/remote_checkin.py:BURST_WINDOW same-root — imported, not copied
hrms/tests/test_an_ignored_tap_does_not_split_the_day.py same-root — census gains the new NOISE writer
Residual (backlog, owner question): a double-OUT day 40 min apart pays to the later OUT (day_plan first-IN/last-OUT) — the engine's pairing setting should decide; an imported IN→IN across midnight leaves both days open for HR (nothing written).

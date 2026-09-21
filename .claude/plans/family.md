# Family — feat(attendance): a roster change re-stamps the punches it covers (21 Sep 2026)
CLASS: derived state (the shift stamp) written once from an editable source (the roster) and never recomputed
New module hrms/utils/restamp.py; hooks on Shift Assignment submit/cancel/after-submit.
hrms/utils/attendance_recovery.py:_plan_rostered_shift / _fix_rostered_day not-affected — the nightly F1 step keeps its own 7-day repair (now guarded, 113146fbc); the job here covers the change as it happens; F1 can later call restamp() (ticket)
hrms/overrides/employee_checkin_override.py:fetch_shift same-root — the one resolution rule, called on the loaded doc; on a loaded doc it clears only shift/offshift, so restamp clears the whole stamp itself
hrms/overrides/shift_assignment_hooks.py:close_superseded_assignments not-affected — ends the old row with db.set_value (no hook); the new assignment's own job covers the range
hrms/utils/day_remark.py:remark_day_after_commit not-affected — reused; pass-owned/today days dropped as for every producer
Not in this slice: the historical glitch range is listed by preview() and written by HR fixing the roster (owner: no console steps; list first).

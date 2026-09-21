# Family — fix(attendance): a heal never queues a rebuild against its own pass (21 Sep 2026)
CLASS: a scheduled pass that saves a punch through the document fires the punch-edit hook, which enqueues a day-remark job at the pass's own commit — the job then races the pass's marking of the same day (the 16 Sep c68597277 class, left open on the heal writer)
Changed symbol: offshift_punch_heal._heal (punch.save inside rebuilding(employee, clock day, shift day)).
hrms/hr/doctype/shift_type/shift_type.py:process_auto_attendance_for_all_shifts same-root — the hourly prelude calls heal_recent_offshift_punches → _heal; fixed by the wrap inside _heal
hrms/utils/attendance_recovery.py:_apply_heal same-root — the nightly heal step calls _heal; same wrap
hrms/utils/offshift_punch_heal.py:heal_offshift_punches (manual) same-root — same writer
hrms/overrides/day_remark_hooks.py:remark_changed_punch_day not-affected — still fires; remark_day_after_commit refuses pass-owned days, which is the mechanism used
hrms/utils/day_remark.py:rebuilding not-affected — the existing context manager, reused
Post-heal marking: links and unlinks are db.set_value writes (employee_checkin.py:914, attendance.on_cancel) — no on_update hook fires there, so wrapping the save is the whole race.

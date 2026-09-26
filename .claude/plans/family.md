CLASS: a surface decides a tap's day by clock date or check-in window, not the work day the attendance record uses
hrms/utils/ot_calculation.py _explain_no_overtime — same-root (fixed: taps_for_day)
hrms/utils/worked_days.py punch_days — same-root (fixed: work_day of the IN)
hrms/api/requests_summary.py unmarked days — same-root (fixed: work_day, was shift_actual_start = window start)
hrms/api/calendar.py month worked map — same-root (fixed: same)
hrms/api/__init__.py claimable summary by_day — not-affected — already shift_start or time
hrms/api/attendance_master_edit.py punch_belongs_to — not-affected — already shift_start or time
hrms/api/attendance_fix_day.py _day_taps — not-affected — already shift_start or time
hrms/scenarios/attendance_pack.py — the real-life pack (9 day shapes, bench, rolled back)

CLASS: a surface decides a tap's day by clock date, not the work day the attendance record uses
hrms/sync/lone_in_closer.py lone_in_days — same-root (fixed: day_of_each)
hrms/api/__init__.py _incomplete_ot_days — same-root (fixed: day_of_each, time-ordered read)
frontend/src/components/ListView.vue checkinDays — same-root (fixed: workDayOf mirror)
frontend/src/views/attendance/EmployeeCheckinList.vue — same-root (asks shift_start)
hrms/utils/work_day.py — same-root (day_of_each added; one rule)
hrms/hr/doctype/shift_type/shift_type.py:999 HR_REMOVED_DEVICE — not-affected — the marker is written on the removed day's own date and read back by the same clock rule (hr_removed_day.removed_days)
hrms/sync/checkin_recovery.py _fill_inferred_types — not-affected — one-off recovery of early-September overwrites; historical repair is the owner's call, not changed

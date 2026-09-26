# HANDOFF
prompt:   alpha.11 — one work-day rule, real-life pack, last sheets audited, HR missed-checkout suggestions
status:   done
commit:   27159520f on nz-glass (tag v2.0.0-alpha.11)
files:    hrms/utils/work_day.py, hrms/sync/lone_in_closer.py, hrms/api/__init__.py
          frontend/src/utils/dayGroups.js, ListView.vue, DaySheet.vue, RequestActionSheet.vue
          hrms/hr/report/missed_checkouts_after_midnight/
          hrms/scenarios/attendance_pack.py
verify:   bench --site fresh.local execute hrms.scenarios.attendance_pack.pack  (9/9 PASS)
flags:    damaged past days stay HR-confirmed, never auto-fixed; checkin_recovery left as is
next:     deploy nz-glass; HR opens "Missed Check-outs After Midnight", ticks a row, presses Punches

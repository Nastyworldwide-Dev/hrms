# HANDOFF
prompt:   defect families behind the 25 Sep report (hunt + fix)
status:   done
commit:   0523b4016 on nz-glass (deploy the branch head)
files:    hrms/api/attendance_fix_day.py
          hrms/api/attendance_fix_days.py
          hrms/api/calendar.py
          hrms/api/__init__.py
          frontend/src/components/CheckinDecisionSheet.vue
          frontend/src/components/glass/GBalanceCard.vue
          docs/glass/audit/2026-09-25-defect-families.md
verify:   Desk Fix attendance on an August day with an old-system Absent row -> Save & rebuild -> Present
flags:    stored "Open" on old submitted requests left as is (every screen now reads it right); no live access to confirm the two On Duty days
next:     owner deploys nz-glass head

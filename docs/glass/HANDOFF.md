# HANDOFF
prompt:   owner report 25 Sep (fix-a-day Open, manager can't see, AL balance, Desk Fix attendance)
status:   done
commit:   446b77b9f on nz-glass (after tag v2.0.0-alpha.7; deploy the branch head)
files:    hrms/api/attendance_fix_day.py
          hrms/tests/test_attendance_fix_day_save_day.py
          frontend/src/utils/requestStatus.js
          frontend/src/components/RequestBalances.vue
verify:   Desk > Employee Checkin > Fix attendance on Norazlin 19 or 20 Aug: pair pre-ticked, Save & rebuild writes Present
flags:    the two On Duty rows (27 Jun, 29 Jul) are already submitted; confirm on live that their attendance exists (not checked: no live access)
next:     owner deploys nz-glass head

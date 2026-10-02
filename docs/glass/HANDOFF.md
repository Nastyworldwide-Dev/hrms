# HANDOFF
prompt:   HR "asal aku takleh update?" on Desk Roster
status:   done
commit:   9dbfb35af on nz-glass (v2.0.0-alpha.31)
files:    roster/src/components/ShiftAssignmentDialog.vue
          roster/src/components/Link.vue
          hrms/api/roster.py
          hrms/api/test_roster.py
verify:   deploy; HR opens Desk Roster, clicks a shift, changes Shift Type -> Update -> that day changes
flags:    none
next:     deploy alpha.31; HR refreshes Desk Roster

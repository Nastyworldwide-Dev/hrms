# HANDOFF
prompt:   alpha.39 "Roster in HR's Hands" (owner rulings R1a-R4a, A6, A7)
status:   done
commit:   4dff516c0 on nz-glass (tag v2.0.0-alpha.39, GitHub Release created)
files:    hrms/hr/doctype/roster_day/ (new doctype: a day off with no shift)
          hrms/api/roster.py (set_day_type, edit one field, HR re-types a worked day, swap)
          hrms/utils/ot_calculation.py (pay reads the day marker first)
          hrms/api/team.py (Nadi roster returns markers)
          frontend/src/views/team/TeamRoster.vue (Assign without a shift, Location, O/R/PH)
          roster/src/components/ShiftAssignmentDialog.vue, MonthViewTable.vue (Desk)
verify:   live site: run migrate (creates Roster Day); Nadi Team roster -> Assign, no shift, Off day -> saves and shows O
flags:    Glass gates CI red on the last 10 pushes (before this release too); Desk month view + drag-swap not checked live;
          day sheet / Team status do not read day markers yet (owner to decide, ticket-team-py-member-statuses.md)
next:     owner puts alpha.39 live and runs migrate; then the day-sheet marker decision

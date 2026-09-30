# HANDOFF
prompt:   supervisor could not assign shifts to own team (HR report) + blank Assign button
status:   done
commit:   2f1b7b8dd on nz-glass (tag v2.0.0-alpha.25)
files:    hrms/hr/utils.py
          hrms/api/roster.py
          hrms/api/team.py
          hrms/overrides/employee_owned_row_scope.py
          hrms/hr/doctype/shift_assignment_tool/shift_assignment_tool.py
          frontend/src/views/team/TeamRoster.vue
verify:   supervisor opens Team roster: "You" first; Assign a report in another company -> "Shift assigned"
flags:    Reports To wins over the company lock (owner ruling); swap/break still company-locked (ceiling marked)
next:     alpha.26 larger text; ticket .claude/plans/ticket-one-my-team-rule.md

# HANDOFF
prompt:   alpha.40 "Days Off Everywhere" (owner, 7 Oct: day marks on every screen; Desk-form shift clears a mark)
status:   done
commit:   efe292f0d on nz-glass (tag v2.0.0-alpha.40, GitHub Release created)
files:    hrms/api/now.py (Home + day sheet: a marked day is a day off)
          hrms/api/team.py (Team status: Off on a marked day)
          hrms/overrides/shift_assignment_hooks.py + hrms/hooks.py (hand-made shift clears the mark)
          hrms/hr/shift_rules.py, hrms/api/attendance_master_edit.py, shift_assignment_tool.py (code-made shifts keep it)
verify:   live site: migrate (alpha.39's Roster Day if not yet); mark a day Off -> Team says Off; add a Desk shift on it -> mark gone
flags:    Glass gates CI red on every push since before alpha.38; pre-existing test failures listed in progress.md
next:     owner puts alpha.39 + alpha.40 live and runs migrate

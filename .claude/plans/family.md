CLASS: the viewer branch REPLACED the Team member list instead of adding to it, and keyed off the raw manager argument instead of "is this my own view"
hrms/api/team.py:get_team_status same-root — company members are added to own reports; viewer branch runs whenever team_of is the caller (manager=self too); a viewer with no Employee record still reaches it
frontend/src/views/team/TeamDashboard.vue:72 same-root — roster link follows hasTeam (the Roster's own gate), not company_view
hrms/api/calendar.py:_team_off_days not-affected — Calendar tab's team line stays direct reports by owner ruling 29 Sep; Team page has its own month calendar
hrms/api/team.py:get_team_roster not-affected — Roster stays reports_to only
hrms/tests/probes/team_line_parity_probe.py:28 not-affected — probe users are managers without the viewer role; their payload is unchanged
hrms/tests/probes/team_line_parity_probe.py:103 not-affected — same: manager summary, no viewer role
hrms/tests/probes/team_line_parity_probe.py:155 not-affected — HR browsing another manager (manager != caller), viewer branch never runs

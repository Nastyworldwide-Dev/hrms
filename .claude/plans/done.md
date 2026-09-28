GOAL: the Calendar day sheet's team line and the Team page never disagree about who is in — both read one member-status rule (punches count before auto-attendance writes its row).
DONE WHEN: calendar.get_day's coverage is counted from hrms.api.team.member_statuses over own_team_members, and carries the same rows as `team`.
CHECK: PYTHONPATH=. python3 -m pytest -q hrms/api/test_calendar_team_matches_team_page.py; bench --site spoke.localhost execute hrms.tests.probes.team_line_parity_probe.scenario (FAIL on HEAD: sheet present 0 / unmarked 3, page Present 2; PASS after).

# Ticket: hrms/api/team.py member_statuses keeps needing fixes (hotspot, 18 commits/90d)

WHY: one function builds the day status, punches, leave and attendance for the Team page AND the Calendar day sheet.
Each fix (half day, midnight punches, member clock, leave) has landed inside it. ticket-roster-py-refactor.md covers roster.py only.

DO: split member_statuses into four small readers (attendance, leave, punches, shift bounds) with one test each, keep the
row shape as is. Do it before the next change to this function, not as drive-by.

NOT NOW: no behaviour change; the parity tests (test_calendar_team_matches_team_page.py) are the safety net.

## Update 7 Oct 2026 (d93c4ab49) — team.py 10 fixes / 90 days
- get_team_roster + _day_markers is the second hotspot in team.py: move the roster read into its own module,
  `markers` part of its row shape, one fence test.
- OPEN (owner): member_statuses and calendar._day_shift do not read Roster Day markers, so a day marked Off
  with no shift shows "O" on the roster but may show a default shift / "No shift" on the day sheet and Team
  status. If they must agree, read it through _classify_day, never a second query.

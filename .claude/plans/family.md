CLASS: a "who is in today" answer computed from Attendance rows alone, which auto-attendance writes after the shift, so punched-in people read as "not in yet"; plus a second, independent definition of "my team" that could drift from the Team page's
hrms/api/calendar.py:_coverage same-root — now counted from team.member_statuses (the Team page's rule)
hrms/api/calendar.py:get_day same-root — team list from team.own_team_members, the Team page's list (owner Q3, 28 Sep: all reports on both screens)
hrms/api/team.py:get_team_status same-root — body extracted into member_statuses / own_team_members, behaviour unchanged
hrms/api/home.py:67 not-affected — days worked already unions paired_days (punch-aware, hrms/utils/worked_days.py)
hrms/api/calendar.py:get_month_flags not-affected — grid dots already use punch_days (punch-aware)
hrms/api/team.py:get_team_roster not-affected — shifts only, no presence
hrms/overrides/approval_row_scope.py:62 not-affected — get_direct_report_employees there is a permission fence (company-fenced on purpose), not a presence count

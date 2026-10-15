CLASS: Team members came only from reports_to, so a company-scoped viewer role had no way onto the Team screen
hrms/api/team.py:get_team_status same-root — viewer branch uses company_members(Company UP)
hrms/api/team.py:get_team_roster not-affected — Roster stays reports_to only; viewers never reach it (has_team false)
hrms/hr/report/shift_attendance/shift_attendance.py not-affected — already fenced by attendance_viewer_companies

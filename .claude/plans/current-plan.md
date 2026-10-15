# Attendance Report Viewer sees their company on Team (owner, 15 Oct 2026)

APPROVED: owner, 15 Oct 2026: "yes, team for mia means everyone in shenzen team. we can just reuse the same existing role as we gave mia. and the company in permission as their lockdown."

FLOW:
Mia opens More -> has_company_view (role Attendance Report Viewer) -> Team row shown, Roster hidden -> get_team_status -> company_members(her Company User Permissions) -> every active employee + day status -> read only, no roster link

MOCKUP: NOT NEEDED (reuses the existing Team screen; only one row hidden and one footer line)

DESIGN SKILLS: NONE (no new UI)

EXPECTED OUTPUT:
- A viewer with Company UP Shenzhen sees every active Shenzhen employee on Team with today's status.
- A viewer with no Company UP sees nobody, never everybody.
- Roster stays hidden; a viewer cannot browse another manager's team.
- Managers, HR and plain staff unchanged.

# Ticket: split get_team_status (hotspot, 16 Oct 2026)

hrms/api/team.py: 24 commits in 90 days. Cause: get_team_status mixes three jobs
(own team, an Attendance Report Viewer's company view, HR browsing another team),
so every new empty state adds a flag (entitled, company_view, no_company).

1. Split it: resolve_scope() -> {kind: own | company | other, companies, members}, then a payload builder.
2. Replace the three booleans with one empty_reason: no_team | no_company | nobody_today.
3. A scope-kind x expected-reason test table (bench-free); keep the bench-only API test thin.

Not in alpha.55. Raised by the review of 09e3353c2.

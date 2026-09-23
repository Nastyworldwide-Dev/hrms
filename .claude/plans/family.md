CLASS: the day sheet's team counted people routed for approval, not the
caller's team (owner ruling 1, 23 Sep 2026): a named approver for a branch
got the branch as "their team", which the Team page never shows.

Callers of get_employees_routed_to for a TEAM view:
hrms/api/calendar.py:get_day — same-root, fixed here (get_direct_report_employees, the Team page's own test).
hrms/api/approvals_list.py / needs_you.py — not-affected: they are about APPROVAL work, where routing is the right group.
hrms/api/team.py has_team — not-affected: already reports_to.

Also (review of 8fc7dbe6a): _event_days swallowed every error; it now
swallows only "the board is not there" (DoesNotExistError or a DB
Programming/TableMissing error) and re-raises the rest.

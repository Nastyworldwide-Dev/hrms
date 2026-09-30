# Supervisor rosters self and own line (HR report 30 Sep 2026)

HR: "dia tak boleh assign shift untuk budak dia". Team roster listed a supervisor's reports by Reports To, then Assign refused them.

## FLOW
TeamRoster.vue Assign -> hrms.api.roster.insert_shift -> _ensure_can_roster_employee -> _ensure_can_roster (HR in company | employee in hrms.hr.utils.rostered_employees) -> create_shift_assignment(ignore_permissions for the admitted line)
employee_owned_row_scope._rostered_by -> rostered_employees (same list); hrms.api.team.get_team_roster puts the supervisor first (is_self)

## MOCKUP: NOT NEEDED (no new screen; the existing row reads "You", the existing button gets its words)

## EXPECTED OUTPUT
- Supervisor with a Company lock assigns a shift to a report in another company: saved.
- Supervisor assigns a shift to themselves: saved; they are listed first as "You".
- A stranger: still refused. No role: nothing rostered.
- The Assign shift button shows its words.

APPROVED: owner, 30 Sep 2026 — "They have the role", "Yes, allow self", "Reports To wins".

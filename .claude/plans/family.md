CLASS: a record name with its company abbreviation shown as a department name.

Call sites: TeamDashboard.vue, TeamRoster.vue, HRIssueBoard.vue (2), SopDetail.vue, SopFormSheet.vue, SopList.vue (2), kpi/Dashboard.vue filter — same-root, fixed via utils/departmentLabel (value unchanged, label only). kpi department tree labels — not-affected (server sends node.label). Team tab lighting More — not-affected, by design (navItems.js lists /team under More).

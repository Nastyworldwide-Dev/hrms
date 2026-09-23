CLASS: an approval surface in two places (AUDIT-PLAN Approvals row: cut the
Requests Team tab) and a past-decision door in system words (ruling 2).

Surfaces and verdicts:
frontend/src/components/RequestPanel.vue — same-root: tabs are "My requests" and, for approvers, "Answered by you" (was My / Team / History); ?tab=answered opens it; empty state says "You haven't answered any requests yet."; the eyebrow that repeated the title is gone.
frontend/src/views/Approvals.vue — same-root: "Requests you've already answered ›" opens Requests on that tab.
frontend/src/data/requestLists.js TEAM_REQUEST_LISTS — not-affected: still reloaded by realtime for Home's counts; only the tab that rendered them is cut.
frontend/src/views/attendance/ShiftRequestList.vue ["My Requests","Team Requests"] — ticket: the per-list Team tabs (AUDIT-PLAN "cut the list-page Team tabs") are a separate slice.

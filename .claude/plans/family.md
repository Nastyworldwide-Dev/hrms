CLASS: a server-formatted string parsed again on the client. approvals_list
sends dates in the person's words; any client formatter that re-parses them
gets "Invalid Date".

Readers of approvals_list row fields:
frontend/src/components/CheckinDecisionSheet.vue whenLine — same-root, fixed here (renders row.when).
frontend/src/views/Approvals.vue rowLine — not-affected: joins row.when as text, never parses it.
frontend/src/views/Approvals.vue summary — not-affected: parses row.modified, which stays ISO (sort key).
frontend/src/views/Approvals.vue answeredLine — not-affected: parses checkin_time from list_decided_for_approver, raw ISO.

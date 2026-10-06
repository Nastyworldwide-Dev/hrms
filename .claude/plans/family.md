CLASS: a refusal shown as a glitch. A detail page the person may not open answered a 403 with "Could not load ... Try again", which invites a retry that cannot work.
frontend/src/components/ResourceError.vue same-root (no-access -> "You can't open this.", no Try again; every view using it gets it)
frontend/src/utils/sessionLost.js same-root (isNoAccess: a 403 from a signed-in person; a session that ended stays the reload onto Login)
frontend/src/views/kpi/KpiDetail.vue not-affected — has no resource; kpi/Dashboard.vue already renders ResourceError for it
frontend/src/components/RequestTimeline.vue, ExpensesTable.vue, ExpenseTaxesTable.vue, MustReadNotice.vue ticket alpha.38 — render nothing on a failed load; listed in /tmp/slices/alpha37-B2B3R1.result.md
frontend/src/utils/loudRequest.js ticket alpha.38 — still toasts "Something didn't load" over the 403 sentence

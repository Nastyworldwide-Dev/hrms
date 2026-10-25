CLASS: a record deleted since it was linked is treated as a connection failure (retry offered, "didn't load" toast)
frontend/src/components/FormView.vue same-root — fixed: isGone card with Back, data-no-access (all 7 request detail screens use FormView)
frontend/src/utils/requestFailure.js classifyFailure same-root — fixed: "gone" verdict, no toast over the card, a plain one elsewhere
frontend/src/components/ResourceError.vue ticket .claude/plans/ticket-load-shifts-oct25.md — still says "Could not load X" + Try again for a 404 (SOP, ticket, issue detail); not changed here
frontend/src/utils/loudRequest.js:34 same-root — wires makeFailureReporter into every frappe-ui request; the gone verdict reaches all screens through it

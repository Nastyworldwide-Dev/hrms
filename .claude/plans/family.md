CLASS: a request type the server can list with no sheet fields on the client.
RequestActionSheet requires `fields`; a type missing from the map throws on tap.

INSTANCE: Approvals.vue kept its own FIELDS map without Compensatory Leave
Request, which get_waiting_for_me lists as "Time off in lieu" (review of be4b81edf).

Call sites of REQUEST_SUMMARY_FIELDS / requestSummaryFields:
frontend/src/views/Approvals.vue — same-root, fixed here (reads the shared map; map covers every listed type, pinned by approvals-page.test.js).
Other readers of the map (forms opening the same sheet) — not-affected: each opens a sheet for its own doctype, all of which were already in the map.

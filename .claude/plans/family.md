# FAMILY — one refused decision, two red toasts

CLASS: a WRITE endpoint whose caller already presents the refusal, still
toasted by the loudRequest seam as "Could not load". Managers photographed
"Could not load" stacked on "Error", the same sentence twice, on every refused
Approve (21 Sep 2026).

Call sites the machine lists for SILENT_ENDPOINTS / makeLoudRequest:

* frontend/src/utils/loudRequest.js SILENT_ENDPOINTS — same-root: adds
  hrms.api.approval.decide (RequestActionSheet.onActionError owns the toast).
* frontend/src/components/RequestActionSheet.vue:339 decision resource +
  :510 onActionError — not-affected: keeps showing "Error" + server reason.
* frontend/src/components/RequestActionSheet.vue finalize
  (hrms.api.approval.finalize) — same-root: same sheet, same onActionError;
  silenced in the follow-up commit (reviewer of f085ff325 asked for it now).
* frontend/src/data/helpdesk.js new_ticket — not-affected: the ticket form
  shows NO toast of its own (the screenshot shows one "Could not load" only),
  so the seam's toast is its only feedback.

Regression test: frontend/src/utils/__tests__/loudRequest.test.js
("a refused request decision is not toasted twice").

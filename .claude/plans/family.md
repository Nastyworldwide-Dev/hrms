CLASS: a request showed its current status but not how it got there
hrms/api/request_history.py — same-root (new: steps from Version rows, fenced by _request_read_allowed, names not logins, only history newer than the document)
frontend/src/components/RequestTimeline.vue + utils/requestTimeline.js — same-root (new: History group under the request)
frontend/src/components/FormView.vue — same-root (renders the timeline on a saved request)
hrms/api/approval.py get_rejection_reason — not-affected — reused as is for the reason line

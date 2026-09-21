# Family — fix(approval): finalize transitions request doctypes only (21 Sep 2026)
CLASS: a whitelisted transition endpoint trusted the caller's native DocPerm instead of naming the doctypes it serves
Changed symbol: `finalize` in hrms/api/approval.py. Callers:
frontend/src/components/RequestActionSheet.vue (finalize resource) not-affected — sends request doctypes only (Attendance Request, OT Request, Replacement Leave Claim, and cancels of every request type), all in DECISION_FIELD_BY_DOCTYPE
frontend/src/components/FormView.vue (finalize on submit/cancel) not-affected — same request doctypes
hrms/api/test_approval.py same-root — new test pins the refusal
Sibling endpoints already allow-listed: `decide` (DECIDE_THEN_SUBMIT), `cancel_for_correction` (DECISION_FIELD_BY_DOCTYPE). No other whitelisted generic submit/cancel found (grep `docstatus` in hrms/api).
hrms/tests/probes/lifecycle_probe.py:316 not-affected — docstring mention; the probe calls doc.submit() directly, not finalize
hrms/tests/probes/lifecycle_probe.py:328 not-affected — docstring mention; the probe re-implements the cancel elevation and never calls finalize

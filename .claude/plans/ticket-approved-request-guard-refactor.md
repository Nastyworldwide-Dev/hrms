# TICKET — hrms/utils/approved_request_guard.py is a hotspot (8 fixes / 90 days)

Opened 17 Sep 2026 alongside the withdrawal work, per the rule that a fix in a
hotspot without a refactor ticket is Important. Raised by the review of
96962182a, which also found the defect this ticket exists to prevent the next
of: a per-doctype map validated for EXISTENCE and not for MEANING.

## What the file has become
Three owner rulings in four days (13, 14 and 17 September), each rewriting who
may cancel an approved request, have left it carrying:

1. `DECISION_FIELD_BY_DOCTYPE` — which field records the decision, per doctype;
2. `REQUEST_PERIOD_FIELDS` — which fields name the days, per doctype;
3. `_paying_salary_slip` — the OT-specific payroll read;
4. `_withdrawal_block` — the general payroll read;
5. `may_cancel` / `cancel_refusal` — the routing and the money rules;
6. `block_cancel_of_approved` — the doc_event that enforces it.

Two per-doctype tables that must agree with each doctype's real schema, and
nothing in the file itself that knows when they do not. That is exactly how
Travel Request came to be checked against `creation`.

## Proposed shape (no behaviour change)
The two tables become one `REQUEST_SHAPE` record per doctype — decision field,
period fields, and how payroll touches it — declared once, beside a single test
that reads every doctype's JSON and fails anything that is not real. The
routing rule and the money rules stay where they are; what stops being possible
is a table drifting from the schema it describes.

## Not now
It is a move, and the invariant test landed in 7e788e996 already carries most
of the safety. Do it when a fourth ruling touches this file, or when the
90-day fix count is still above 6 at the next retro.

## Related
`.claude/plans/ticket-approval-refactor.md`,
`.claude/plans/ticket-attendance-request-refactor.md`,
`.claude/plans/ticket-remote-checkin-refactor.md`,
`.claude/plans/ticket-unfenced-self-submission.md`.

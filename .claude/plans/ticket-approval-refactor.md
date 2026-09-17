# TICKET — hrms/api/approval.py is a hotspot (16 fixes / 90 days)

Opened 17 Sep 2026 alongside the self-approval fix, per the rule that a fix in
a hotspot without a refactor ticket is Important. Raised again by the reviewer
on that commit.

## What the file has become
`_decision_access` is now four policies read top to bottom in one function:

1. is this doctype decidable at all, and is a Workflow governing it,
2. may the caller SEE the request (company fence),
3. is the caller the applicant — and if so, does the chain of command or an
   HR Settings tickbox refuse them,
4. do they have native rights, or are they the routed approver.

Each fix has added a branch to (3). This one added two module constants and a
helper; the one before added the company fence; the one before that added the
"decided draft" path. The policy is legible only by reading the whole function
in order.

## Proposed shape (no behaviour change)
A `DecisionPolicy` — one small module holding the doctype table
(`DECIDE_THEN_SUBMIT`, `SELF_APPROVAL_SETTING`, `APPROVER_SOURCE`) and one
`refusal(doc, status, user) -> str | None` that returns the REASON a decision
is refused, or None. `_decision_access` then reads: read fence, refusal,
native-or-routed. The reason string is what the endpoint shows the caller,
which also fixes today's single flat "You are not permitted to decide this
request" for four different causes.

## Not now
It is a pure move and earns nothing on its own. Do it when the next change
would otherwise add a fifth branch to `_decision_access`, or when the 90-day
fix count on this file is still above 12 at the next retro.

## Related
`.claude/plans/ticket-remote-checkin-refactor.md` — the same rule, same day,
for `hrms/api/remote_checkin.py`.

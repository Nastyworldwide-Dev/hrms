# TICKET — two request types have no self-approval fence at all

Found 17 Sep 2026 while reviewing the self-approval fix. Not a regression: it
has never been wired.

## What is missing
`hrms/utils/approved_request_guard.py::DECISION_FIELD_BY_DOCTYPE` models
**Employee Advance** and **Travel Request** with `field = None`, which in this
codebase means "submitting IS approving". But:

* neither controller calls `hrms.hr.utils.validate_self_submission`,
* neither appears in `DECIDE_THEN_SUBMIT` (so `_decision_access` never sees them),
* neither is in `SELF_APPROVAL_SETTING`,
* neither is in the canonical-fence AST list.

So submitting your own Employee Advance or Travel Request is a plain
docstatus-submit governed only by DocPerm. Every other request type in the app
refuses that — five outright, two through the chain of command.

## Actual exposure today
Lower than it reads. Employee Advance is **hidden from the PWA** by the owner's
15 Sep ruling, and Travel Request has no PWA surface either, so the reachable
path is Desk-only, for someone who already holds submit rights there.

## The fix when it is wanted
Add both to the `validate_self_submission` callers (their `before_submit`), and
add them to `hrms/tests/test_self_approval_fences_are_canonical.py::FENCES` so
they cannot drift back out. Decide first whether either should instead route
through an approver, which would make them `DECIDE_THEN_SUBMIT` members with a
chain-of-command rule like Leave and Expense.

## Why it is a ticket and not part of that commit
It is a policy extension to two doctypes the reported defect never touched, and
the reviewer's own recommendation was to keep it out of that diff. Needs the
owner's word on whether these two doctypes are in use at all.

## Related
`.claude/plans/family.md` (the 17 Sep self-approval family),
`.claude/plans/ticket-approval-refactor.md`.

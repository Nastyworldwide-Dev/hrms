# FAMILY — an approver with an approver above them approves their own request

CLASS: a self-approval refusal made OPTIONAL by a site setting. Five of the
seven approvable doctypes refuse a self-decision outright in
`hrms/api/approval.py::_decision_access`. Leave Application and Expense Claim
refused only while an HR Settings tickbox was on
(`prevent_self_leave_approval`, `prevent_self_expense_approval`, doctype
default 0, one click to untick, no trace on the request). A fence whose whole
authority is a tickbox is not a fence, and the reporting line never entered
the decision at all.

Second, narrower defect in the same function: the "is this me?" test was a raw
`Employee.user_id` read, the exact shape every other self-approval fence was
moved OFF after it failed OPEN — see
`hrms/tests/test_self_approval_fences_are_canonical.py`, whose AST list did
not include `hrms/api/approval.py`.

ROOT CAUSE: `_decision_access` — fixed there, once, for every caller. The
refusal now asks `hrms.hr.utils.is_own_employee` and, for the two doctypes with
a tickbox, whether `get_designated_approvers` finds anyone above the applicant.

OWNER RULING, 17 Sep 2026, on the top of the chain: "they dont have to.
nothing. if and in my company only one. system might detect. this is to fix
the ones who can self approve despite having their reported to, which is
wrong." An empty approver list is the detection; that case is untouched.

## Every call site of `_decision_access`

hrms/api/approval.py:303 (`decide`) — same-root (fixed here)
  The reported symptom: the PWA and Desk decision endpoint. Refuses with
  PermissionError when access is None, so the new refusal lands here.
hrms/api/approval.py:373 (`get_decision_actions`, pending) — same-root (fixed here)
  Builds the Approve/Reject buttons from the same helper, so the Approve
  action simply stops being offered. No separate rule to keep in step.
hrms/api/approval.py:374 (`get_decision_actions`, decided draft) — same-root (fixed here)
  The "Submit" affordance for an already-decided draft, same helper.
hrms/api/approval.py:498 (`finalize`) — same-root (fixed here)
  The legacy submit path, which calls the helper precisely so a decided draft
  cannot bypass the gate.
hrms/api/approval.py:120 (`_is_routed_approver`) — not-affected
  Unchanged by owner ruling R2 ("Leave it exactly as is, no report"). HR roles
  keep company-wide authority; the self-check runs BEFORE routing, so this
  function never sees a self-decision it could allow.
hrms/hr/doctype/leave_application/leave_application.py:960 — not-affected
  `validate_for_self_approval`, the Desk-side twin. Still governed by the
  tickbox, and already canonical (`is_own_employee`). It guards a save; the
  decision path above guards the decision, and reaches it first.
hrms/hr/doctype/expense_claim/expense_claim.py:207 — not-affected — same shape.
hrms/hr/utils.py:1067 (`validate_self_submission`) — not-affected
  The unconditional fence for the five doctypes that never had a tickbox.
  Already canonical, already refuses.

## Second pass, 17 Sep 2026 — the same class behind the Desk door

Review of e3ef2f4de found the fix closed the API door only. Both are now
fixed at the one shared helper, `hrms.hr.utils.has_approver_above`:

hrms/hr/doctype/leave_application/leave_application.py:960
  (`validate_for_self_approval`) — same-root (fixed here)
  The Desk approves by SAVING and never reaches `_decision_access`. This
  validator was still tickbox-only, so the reported person could open their own
  leave in Desk, set Approved and submit.
hrms/hr/doctype/expense_claim/expense_claim.py:207
  (`validate_for_self_approval`) — same-root (fixed here)
  Same shape. The new refusal is scoped to an APPROVED claim, because
  submitting a claim of your own is how it is filed.
hrms/utils/approved_request_guard.py:64 (`is_own_request`) — same-root (fixed here)
  The raw `Employee.user_id` compare this fix declared non-canonical, left in
  the guard that refuses CANCELLING an approved request. Under-matching there
  let the employee cancel their own approved request. `is_own_employee` can
  only match more often, which for a refusal is the closed direction.
hrms/overrides/approval_row_scope.py:97 (`has_permission`) — not-affected
  Grants the employee write/submit on their OWN request by design (that is how
  a request is filed and withdrawn). It is a ROW scope, not a decision fence;
  the decision is policed by the two validators above and by
  `_decision_access`, which now agree.

## Machine-listed call sites of the changed names

hrms/hr/doctype/attendance_request/attendance_request.py:199 — not-affected — its validate_for_self_approval already refuses every self-approval outright (no tickbox, no chain to consult); it is stricter than the new rule, not looser.
hrms/hr/doctype/remote_checkin_request/remote_checkin_request.py:143 — same-root (fixed here) — reads `not is_own_request(...)` to decide who may approve a remote punch, so it inherits the canonical resolver through the shared helper; the migration can only make it match MORE often, which for a refusal is the closed direction.
hrms/tests/probes/lifecycle_probe.py:339 — not-affected — a probe script, not a fence; it reads the same helper and reports what it sees.

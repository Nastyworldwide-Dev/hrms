# PLAN — nobody decides their own request, and the selfie is never role-gated

Owner report, 17 Sep 2026: "someone who is an approver, yet have their own
approver (higher up/reported to) somehow able to approve its own leave/medical/
etc. the chain of role in command aren't working correctly." Plus: "the selfie
must work for everyone, no role gated. a must."

## What the code actually says (read today, not guessed)

**Finding 1 — self-approval is optional, and only for two doctypes.**
`hrms/api/approval.py::_decision_access` refuses a self-decision outright for
OT Request, Attendance Request, Replacement Leave Claim, Shift Request and
Compensatory Leave Request. For **Leave Application** and **Expense Claim** it
refuses only when an HR Settings tickbox is on:

    prevent_self_leave_approval      (HR Settings, doctype default = 0)
    prevent_self_expense_approval    (HR Settings, doctype default = 0)

`hrms/patches/v15_99_0/staff_perm_lockdown.py::set_self_approval_flags` turns
both on, so a site that ran that patch is covered — until someone unticks them,
which is one click in HR Settings and leaves no trace on the request.

This is not an inference. The behaviour is pinned as EXPECTED by two tests:

* `hrms/api/test_decision_access.py::test_self_policy_matches_all_six_controller_settings`
  asserts `allowed = dt in {"Leave Application", "Expense Claim"} and not prevent`
  for a user holding Employee + **HR Manager** deciding their **own** request.
* `hrms/api/test_decision_access_properties.py:129-131` encodes the same rule.

**Finding 2 — that one fence is the only one that is not canonical.**
`_decision_access` asks `frappe.db.get_value("Employee", employee, "user_id")`
and compares it to the session. Every other self-approval fence in the app was
moved to `hrms.hr.utils.is_own_employee` (own_employees + user_id, fails
closed) after this exact shape failed OPEN before — see
`hrms/tests/test_self_approval_fences_are_canonical.py`, whose AST test lists
the doctype validators and **does not list `hrms/api/approval.py`**. So a
person whose request sits on an Employee row with a blank or duplicated
`user_id` is not recognised as themselves, and decides their own request even
with the tickboxes on.

**Finding 3 — HR authority is company-wide, by design.**
`_is_routed_approver` grants any holder of HR User / HR Manager / System
Manager the right to decide every request in their company, ignoring the
reporting line. That is deliberate and documented. It becomes the reported
symptom when a supervisor is given the "HR" role profile, which bundles HR User
with the approver roles — already recorded as the cause of the HR-only Issue
Board leak. This is role hygiene, not a code defect, but it is invisible: no
screen says who holds it.

**Finding 4 — the selfie is already not role-gated.**
`hrms.api.remote_checkin.upload_selfie` (shipped today) calls `require_employee()`
and nothing else: no role check, no HR Setting, no company fence. It stores the
file with `ignore_permissions`, so a site that forbids public uploads below
System Manager no longer refuses it. Every person who can punch can attach a
photo. No change needed; recorded here as the owner's standing requirement so a
later "hardening" pass cannot quietly re-gate it.

## FLOW — superseded

The first draft of this section proposed an UNCONDITIONAL refusal and a
diagnostic report. Both were answered by the owner below; the binding version
is **REVISED FLOW**, further down. Kept as a pointer so the change of mind is
on record rather than silently rewritten.

MOCKUP: NOT NEEDED (no new screen, control or copy — the PWA already hides
Actions it is not offered by the server, and this changes only what the server
offers. The one user-visible string is a refusal message on an existing path.)

## EXPECTED OUTPUT

* An approver with a manager above them opens their own leave: the Approve
  button is gone; Reject remains. Desk save refuses with the named approvers.
* The same person's report's leave: unchanged, they approve as today.
* Both HR Settings tickboxes can be off and nothing opens up for anyone who
  has an approver above them.
* Selfie: unchanged, works for every employee, no role involved.

## OWNER RULINGS, 17 Sep 2026 (both questions answered)

**R1 — the top of the chain.** "they dont have to. nothing. if and in my
company only one. system might detect. this is to fix the ones who can self
approve despite having their reported to, which is wrong."

So the new refusal is CONDITIONAL on somebody being above the applicant — a
reporting manager, the approver on their Employee record, or an approver on
their department. A person with nobody above them keeps today's behaviour
exactly, including the HR Settings tickboxes. Nothing can be stranded, and the
single-person company needs no setting: an empty approver list IS the
detection.

**R2 — HR's blanket authority.** "Leave it exactly as is, no report."
Finding 3 is OUT OF SCOPE. No change to `_is_routed_approver`, and step 5 (the
diagnostic report) is dropped from this plan.

## REVISED FLOW — what actually changes

1. `_decision_access` asks `hrms.hr.utils.is_own_employee`, like every other
   self-approval fence (Finding 2).
2. When the applicant is the caller, the request is being APPROVED, and
   `get_designated_approvers` returns at least one person, the decision is
   refused — whatever the HR Settings tickboxes say. The tickboxes may only
   make the rule stricter, never looser.
3. Rejecting your own request is a withdrawal and is unchanged.
4. Nobody above them: unchanged, today's rules apply.
5. `hrms/api/approval.py` joins the canonical-fence list in
   `hrms/tests/test_self_approval_fences_are_canonical.py`.
6. `test_decision_access.py::test_self_policy_matches_all_six_controller_settings`
   and `test_decision_access_properties.py` are AMENDED to the new policy (they
   currently pin the defect as expected behaviour), not deleted.
7. The selfie stays exactly as shipped: `require_employee()` and no role gate.
   Recorded as a standing requirement (Finding 4).

## Pipeline Summary

requirements (owner report, above) -> this plan -> owner approval -> red tests
first (`hrms/api/test_decision_access.py` amended to the new policy, a new
canonical-fence entry, a new "names the real approver" test) -> implementation
in `hrms/api/approval.py` -> mapped + importer tests -> commit with the family
ledger (every caller of `_decision_access`: `decide`, `can_decide`,
`get_decision_actions`, the cancel branch) -> hook-dispatched review ->
push -> Nabil deploys. No schema change, no migration, no data repair.

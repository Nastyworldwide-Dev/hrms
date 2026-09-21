# Family — fix(approval): a superior named as approver can open and decide an On Duty request (21 Sep 2026)

CLASS: for the three request doctypes that carry NO approver field of their own (Attendance
Request, OT Request, Replacement Leave Claim), every fence equated "superior" with `reports_to`
alone, and their `employee` link was left fenced by User Permissions. A superior who is instead
the employee's named `leave_approver`, or a Department Approver, was refused READ before any
decision gate ran — so the PWA rendered no Approve button, the Team queue was empty, the
notification went to Administrator, and `decide()` threw PermissionError. Reported as "Superior
cannot approve on duty application ... still persist" — the two earlier fixes (d4494a658,
bdbfd5005) were validation-layer, which is why it survived them.

Bench evidence (probe_on_duty_approve4.py, test.local): before — A reports_to True/Approved,
B named approver read False routed False actions [] PermissionError, C department approver same.
After — all three read True, routed True, actions ['Approved','Rejected'], DECIDE Approved.

hrms/hr/utils.py get_employees_routed_to same-root — new inverse of get_designated_approvers; the one list all four fences now read
hrms/overrides/employee_owned_row_scope.py same-root — TEAM_REVIEWED read admission widened from reports_to to every routed superior, still READ only
hrms/overrides/ot_row_scope.py same-root — same class on OT Request + Replacement Leave Claim; _reporting_employees replaced (it is a subset). has_permission was ptype-BLIND, so the widening first handed a department approver write/submit/cancel on another employee's draft (adversarial verifier, 21 Sep); now gated on ptype == "read" like the sibling fence, red proved on the un-gated version
hrms/api/approval.py _is_routed_approver same-root — DESIGNATED_APPROVER_DOCTYPES; the gate that threw PermissionError
hrms/mixins/pwa_notifications.py _get_ot_approver same-root — the approver was never told; now walks get_designated_approvers before HR fallback
hrms/hr/doctype/{attendance_request,ot_request,replacement_leave_claim}.json same-root — employee link gains ignore_user_permissions, as Leave Application/Expense Claim/Shift Request always had
hrms/patches/v16_0/approver_reads_past_employee_user_permissions.py same-root — the JSON alone is shadowed on a live site by a Property Setter; the patch writes the DocField and strips the override
hrms/utils/decision_field_guard.py not-affected — delegates to _decision_access, so it widens with the fix by design; test_decision_field_guard green
hrms/api/__init__.py get_filters not-affected — line 968 already excludes these three from approver-field filtering; the Team queue rides on the row scope, which is what was fixed
hrms/api/__init__.py _may_read_employee not-affected — already admitted designated approvers (test_employee_read_fence_admits_approvers); this fix brings the request fences up to it
hrms/overrides/approval_row_scope.py not-affected — Leave Application / Expense Claim / Shift Request name their approver ON THE DOC, so the named approver already matched; different shape, no gap
hrms/hr/utils.py get_direct_report_employees not-affected — still the one definition of "my team"; get_employees_routed_to consumes it rather than duplicating it
hrms/mixins/pwa_notifications.py _ot_approver_can_receive not-affected — calls _is_routed_approver, so it widens with the fix; that is the intended coupling
frontend/src/utils/cancelRule.js not-affected — defers to hrms.api.approval.can_cancel_approved; no second copy of the routing rule in the PWA
frontend/src/utils/team.js not-affected — the Team ROSTER is a reports_to view by design (who works for whom), a different question from who may approve
hrms/tests/test_ot_row_scope.py same-root — its AST guard pinned the DELETED _reporting_employees; repointed to get_employees_routed_to (same invariant: no local employee query) and given the ptype-gate assertion, red proved on the un-gated version
hrms/api/test_approval.py same-root — a SECOND copy of the same single-field Employee stub, caught by the pre-commit blast-radius run; taught the as_dict list shape like the other three
hrms/tests/{test_hr_own_request_create,test_restore_staff_create_on_pwa_requests,test_approved_request_guard}.py same-root — stubs pinned the replaced collaborator / a single-field Employee read; repointed, no production behaviour changed

LOCK: hrms/tests/test_a_named_approver_can_decide_an_on_duty_request.py — the regression (the
reported Attendance Request instance) plus the invariant for the class: OT Request and
Replacement Leave Claim must admit and route the same superior, a stranger must still be
refused, and the admission must stay READ-only — asserted on ALL THREE doctypes,
not just Attendance Request, which is the assertion whose absence let the OT/RLC fence
drift ptype-blind in the first place.

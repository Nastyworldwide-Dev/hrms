# FAMILY — "You can only file requests for yourself." on an APPROVAL

CLASS: a FILING-time authorisation rule evaluated on EVERY save, so it also
judges approval saves — on doctypes where approval IS a save, because they
carry no approver field. The guard's exemption list (HR / self / Employee
writer) has never heard of the reporting manager, whom this app's own row
scope names "the natural approver". Two fences, disagreeing, and the narrower
one won.

ROOT CAUSE: hrms/hr/utils.py::validate_filing_for_self — no is_new /
employee-changed test. Fixed there, once, for every caller.

## validate_filing_for_self — the defective guard

hrms/hr/doctype/ot_request/ot_request.py:97 — same-root (fixed here)
  The reported symptom, HR-OTR-26-09-00009. Status Open/Approved/Rejected,
  no approver field, so approving is a save and the approver was refused.
hrms/hr/doctype/replacement_leave_claim/replacement_leave_claim.py:38 — same-root (fixed here)
  Identical shape: Open/Approved/Rejected, no approver field, submittable.
  Its approvers hit the identical refusal; nobody had reported it yet.
hrms/hr/doctype/employee_issue/employee_issue.py:21 — same-root (fixed here)
  Status Open/In Progress/Completed. Whoever moved an issue that was not
  their own was refused the same way.
hrms/hr/utils.py:1060 — same-root (the fix itself)
  The new `_is_filing` gate, called once at the top of the guard.

## validate_self_submission — NOT the same class

Different question, different trigger: it fires only when the SUBMITTER IS
the employee named on the request, to stop self-approval. An approver is by
definition not that employee, so it never fires on the reported path and
cannot produce the reported message. Verified by reading each site; none
reference the filing rule or its exemption list.

hrms/hr/doctype/ot_request/ot_request.py:216 — not-affected — fires only when
  submitter == doc.employee; an approver is never the employee on the row.
hrms/hr/doctype/replacement_leave_claim/replacement_leave_claim.py:94 — not-affected — same rule, same reason.
hrms/hr/doctype/shift_request/shift_request.py:51 — not-affected — same rule,
  and Shift Request additionally HAS an approver field, so its routing already
  names who may act; it never called the filing guard at all.

## LOCK THE CLASS

- Regression test for the instance AND the class:
  hrms/tests/test_filing_guard_is_filing_only.py — bench-free, 7 cases,
  proven RED on HEAD at the exact production message.
- Real-save evidence: verify-bench/sites/probe_ot_approval.py — 7/7, savepoint
  rolled back; RED on HEAD ("APPROVER REFUSED: You can only file requests for
  yourself."), GREEN after.
- The invariant pinned: authority over an EXISTING row is the row scope's
  question (ot_row_scope / employee_issue_row_scope). This guard may only ask
  who chose the subject, and only while the subject is being chosen.

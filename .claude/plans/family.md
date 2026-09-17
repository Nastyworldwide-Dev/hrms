# FAMILY — a permission granted in one place and refused in three others

CLASS: one rule kept in four copies. "Who may cancel an approved request" was
written in the guard, re-derived in `finalize`, re-derived again in the PWA's
`cancelRule.js` — in a file whose own comment says it does not keep a copy —
and asserted in each of their tests. Granting the employee the right to
withdraw in the guard alone would have produced a permission nobody could
reach: the server would say yes and every door would still say no.

Owner, 17 Sep 2026: "approved leave or others made by request (the employee)
can be withdrawn and whatever the approved must be reverted back to its
original content... i have 14 days leave balance... i withdrawn. it must
reflect back to 14 days." Asked which shape, he answered "withdrawal. a." —
outright, by the employee. This reverses his own 14 Sep ruling, which the guard
recorded as "The employee who raised it, and anyone else, still cannot."

ROOT CAUSE: the copies. `may_cancel` is now the one routing answer and every
door asks it.

## Every copy, and the reverting half that already worked

hrms/utils/approved_request_guard.py::cancel_refusal — same-root (fixed here)
  The authority. The owner is allowed; the two money refusals stay.
hrms/utils/approved_request_guard.py::may_cancel — same-root (added here)
  The routing half on its own, so `finalize` can ask it without reading
  payroll a second time on a path that checks payroll moments later anyway.
hrms/api/approval.py::finalize — same-root (fixed here)
  It elevated only for `not is_own_request(doc) and _is_routed_approver(doc)`.
  That second copy is exactly what would have left the owner outside.
frontend/src/utils/cancelRule.js — same-root (fixed here)
  Returned `false` for the owner, so the button never rendered. It now returns
  "approved" for everyone and lets the server answer, which is what its own
  comment always claimed it did.
hrms/api/approval.py::can_cancel_approved — not-affected
  Already answers with `cancel_refusal`, so it inherited the new permission
  without a change. The one door that was built right.
hrms/hr/doctype/leave_application/leave_application.py::on_cancel — not-affected
  `create_leave_ledger_entry(submit=False)` reverses the ledger: 13 back to 14.
hrms/hr/doctype/compensatory_leave_request/compensatory_leave_request.py:142
  — not-affected — takes the allocated days back off the allocation.
hrms/hr/doctype/ot_request/ot_request.py:265 — not-affected — reverses the
  replacement leave it granted, from the stored day count.
hrms/hr/doctype/replacement_leave_claim/replacement_leave_claim.py:145 —
  not-affected — the shared `reverse_replacement_leave`.
hrms/hr/doctype/attendance_request/attendance_request.py:205 — not-affected —
  cancels the Attendance rows the approval created.
hrms/hr/doctype/shift_request/shift_request.py:77 — not-affected — cancels the
  Shift Assignment it created.
hrms/api/correction_cancel.py — not-affected
  The HR-only endpoint for the two doctypes with no decision field. Its own
  role gate is unchanged; this ruling is about the employee's own request.

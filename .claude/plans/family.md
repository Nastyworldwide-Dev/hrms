# FAMILY — an Attendance Request that can no longer be decided

CLASS: a FILING rule re-run at DECISION time. `validate` runs on every save;
`decide()` writes the status and submits in one save, so a check meant to stop
an employee filing a no-op request ran again when the manager tapped Approve.
The day had been marked since filing (punches / mirror), so the request could
be neither approved nor rejected — a rejection is the same save. Reported
21 Sep 2026 on verifica-live: "No attendance to create: 07-08-2026
(Attendance status unchanged)" on every tap.

Call sites the machine lists for validate_no_attendance_to_create /
status_unchanged / get_attendance_warnings:

* hrms/hr/doctype/attendance_request/attendance_request.py:41 validate — same-root:
  the guard sits inside the method, so the filing path is unchanged and only a
  decided request skips it.
* hrms/hr/doctype/attendance_request/attendance_request.py:449 status_unchanged —
  not-affected: a pure read, still feeds the warning list.
* hrms/hr/doctype/attendance_request/attendance_request.py:470 get_attendance_warnings —
  not-affected: whitelisted for the Desk form's warning table, read-only.
* hrms/hr/doctype/attendance_request/attendance_request.js:12 frm.call — not-affected:
  Desk shows the same warnings; the refusal itself only ever came from validate.
* hrms/api/approval.py:300 decide → doc.submit() — same-root by consequence: the
  submit now reaches on_submit, where `create_or_update_attendance` treats an
  already-marked day as the no-op it is.

Sibling doctypes checked for the same class (a validate-time throw whose truth
can change between filing and decision): OT Request, Shift Request,
Compensatory Leave Request, Replacement Leave Claim — their validate() rules
judge the request's own fields (dates, self, overlap with OTHER requests),
which the decision does not move. Leave Application's balance check is
upstream and by design. not-affected.

Regression test: hrms/tests/test_attendance_request_decision_is_always_possible.py
Invariant: a decided request never re-runs the filing refusal (the three cases
Open / Approved / Rejected in that file).

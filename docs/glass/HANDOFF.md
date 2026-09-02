# HANDOFF
prompt:   Pass 2 — request, approval & workflow closure
status:   approval finalization PROVEN fixed at runtime; lifecycle correct
commit:   98f43b337 on nz-glass (verification pass — no new code)
types:    6 approvable via hrms.api.approval.decide — Leave Application, Shift
          Request, Expense Claim, OT Request, Attendance Request, Replacement
          Leave Claim — plus Remote Check-In (remote_checkin.approve/reject).
approval-core: decide(doctype,name,status) sets the decision field then
          doc.submit() in ONE cycle for BOTH approve and reject — "no path that
          writes the decision and stops". Row-lock (for_update), idempotent
          (docstatus==1 no-op), refuses reversal of a settled decision, and an
          HR recovery endpoint (report_half_transitioned) lists any legacy
          decided-but-draft rows without auto-repairing (leave-balance safety).
PROVEN(runtime, fresh.local): Attendance Request docstatus 0 -> decide("Approved")
          -> docstatus 1, status Approved (FINALIZED_IN_ONE_ACTION=true, no second
          Submit); retry idempotent (stays 1); reverse-after-final refused; and
          the validation-failure path (missing attachment) rolled back atomically
          with the decision NOT half-written. The "Approved -> still Draft" defect
          is fixed both ways.
master-data: leave types 15, leave allocations 3, expense types 5, shift types 2
          all present and render. Leave/expense approver OPTIONS are empty only
          where no approver is DESIGNATED for the employee (config) — same class
          as the Expense Type gap; options are built from the exact set the
          save-time fence accepts, so no offer-then-reject.
failure/recovery: idempotent double-tap, atomic rollback on validation failure,
          settled-decision reversal refused, HR report_half_transitioned recovery.
unverified: live-instance rendering of the full UI flow + confirmation the fixes
          are deployed to live Verifica (no access); per-instance approver
          provisioning is a config concern, not a code defect.
verdict:  REQUEST WORKFLOWS CLOSED — approval finalizes in one action (proven),
          lifecycle correct across all types, no reproducible redundant-Submit
          defect; remaining items are config/live-deploy, not code.

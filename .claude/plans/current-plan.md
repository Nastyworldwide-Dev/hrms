# Plan: Manpower Request is hidden from Administrator (owner, 29 Oct 2026)

Owner: a Manpower Request carries salary, so only the sender, the approver and HR see it — "admin is not hr so cannot".
Asked and answered:
- Who sees it: keep today's line — the sender, the person it was sent to for approval (DocShare), and HR (HR User /
  HR Manager). Verified 29 Oct: Nik's own manager (the CEO) cannot open Hafiz's request today; no backup reader added.
- Administrator: hide it everywhere the app controls.

## GOAL
The Administrator account (and System Manager without an HR role) sees no Manpower Request in Desk or Nadi unless it is
their own, shared with them for approval, or they hold an HR role.

## FLOW
Desk list / report view / export -> permission_query_conditions -> employee_owned_row_scope: Administrator no longer
"return everything" for Manpower Request -> own + shared, or 1=0
Desk form -> doc.has_permission -> frappe returns True for the literal Administrator BEFORE app hooks -> so the
controller's onload refuses: ManpowerRequest.onload throws PermissionError unless HR role / own / shared
HR board (hrms.api.manpower.hr_board) + Manpower Requests report -> holds_hr_role() (HR role only), not
is_hr_operator() (which answers True for Administrator)
Known gap, by Frappe design: /api/resource/Manpower Request/<name> for the literal Administrator account.

DESIGN SKILLS: NONE (permission rule, no screen)

## MOCKUP: NOT NEEDED (no screen change)

## EXPECTED OUTPUT
Bench-free tests red first: Administrator list condition is 1=0 (others unchanged); has_permission False for
Administrator on someone else's request; form onload refuses Administrator, allows HR/own/shared; board and report
refuse Administrator and System Manager, allow HR. Other doctypes keep Administrator as before.

## RISK
Administrator loses sight of one doctype, by design. HR keep everything. Rollback: revert.

## Pipeline Summary
owner rule -> plan -> TDD -> commit -> review -> push -> release -> owner deploys (no migrate).

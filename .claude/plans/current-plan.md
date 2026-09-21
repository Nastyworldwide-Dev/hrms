# Remote Check-in Request routes up the employee's own chain

APPROVED by the owner, 21 Sep 2026. I described the change in plain words
("make remote check-in route up the same chain and drop the department tier")
and the answer was "sure".

## The defect
Remote Checkin Request is the one request type the 21 Sep routing ruling never
reached. It does not call `get_designated_approvers`, so the family hunt (a
call-site sweep) could not see it. It still carries the two behaviours the
owner refused:

  1. ONE HOP. `may_decide` -> `_is_routed_approver`, and Remote Checkin Request
     is in none of approval.py's routing maps, so it falls through to
     `reports_to` only. The grand-manager — the escalation when the immediate
     approver forgets — gets PermissionError. This is the reported defect,
     verbatim, for this doctype.
  2. DEPARTMENT BLANKET. `resolve_approver` tier 2 reads a
     `Department Approver` row. Owner ruling 21 Sep: "no, dont".

## FLOW (after)
file a remote punch
  -> resolve_approver stamps approver = chain[0]   (Employee field, else
     reports_to, else the HR-Manager fallback unchanged)
  -> notification addressed to that person          (unchanged path)
  -> anyone on that employee's chain may decide     (NEW: approval.py map)
  -> and sees it in their pending queue             (NEW: queue widened)

## MOCKUP: NOT NEEDED (server-side routing only — no screen, wording or field changes)
Server-side only. No new screen, no changed wording, no new field. The PWA
renders the same queue rows and the same Approve/Reject sheet it renders today;
the only difference is WHICH rows reach a senior approver.

## EXPECTED OUTPUT
  * `resolve_approver(E)` returns the first entry of
    `get_designated_approvers(E, "shift_request_approver", "shift_request_approver")`,
    and never a `Department Approver` login.
  * `may_decide(row, grand_manager)` is True where it is False on HEAD.
  * `may_decide(row, department_approver)` is False.
  * `may_decide(row, own_employee)` stays False (self-decision unchanged).
  * `_pending_for_approver_query` returns the row for the grand-manager as well
    as the stamped approver, still inside the company fence.
  * The HR-Manager fallback, the company fence and the self-decision refusal are
    byte-for-byte unchanged.

## FILES
  hrms/overrides/remote_checkin_request_hooks.py   resolve_approver tiers 1-3
  hrms/api/approval.py                             DESIGNATED_APPROVER_DOCTYPES
  hrms/api/remote_checkin.py                       _pending_for_approver_query
  hrms/tests/test_remote_checkin_routes_up_the_chain.py   NEW

## OUT OF SCOPE
  * hrms/api/team.py's Department Approver tab gate — display only, the queues
    fence themselves. Ticketed, not fixed here.
  * Consolidating the two chain walkers (existing ticket).

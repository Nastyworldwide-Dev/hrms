CLASS: a request type routing by its own private copy of the approver rule.
The 21 Sep ruling ("the chain goes until they dont have"; "no, dont" to the
department blanket) was applied to seven request types through one shared
resolver. Remote Checkin Request never called that resolver — it carried its
own one-hop lookup with `Department Approver` as tier 2 — so a call-site family
hunt could not see it, and it kept both refused behaviours: nobody above the
stamped approver could decide a remote punch, and a department blanket could be
stamped on one.

Instance test: hrms/tests/test_remote_checkin_routes_up_the_chain.py
Invariant test: same file, TestTheThreeSurfacesAgree — everyone the chain names
  must be able to decide, so the stamp, the decision gate and the queue cannot
  drift apart again.

Call sites of resolve_approver / may_decide / _pending_for_approver_query /
DESIGNATED_APPROVER_DOCTYPES:

hrms/overrides/remote_checkin_request_hooks.py:79 same-root — resolve_approver
  itself; now reads get_designated_approvers and stamps chain[0].
hrms/api/approval.py:68 same-root — the routing map; Remote Checkin Request
  added, which is what lets the rest of the chain decide.
hrms/api/approval.py:135 same-root — the only read of that map; unchanged code,
  the new entry reaches the decision through it.
hrms/api/remote_checkin.py:204 same-root — _ensure_approver's may_decide import;
  the PWA decision path, widened by the map above.
hrms/api/remote_checkin.py:207 same-root — the call itself.
hrms/hr/doctype/remote_checkin_request/remote_checkin_request.py:49 same-root —
  the Desk save gate, same helper, same widening. One rule, both surfaces.
hrms/api/remote_checkin.py:325 same-root — list_pending_for_approver; the queue
  now admits routed employees as well as the stamped name.
hrms/api/remote_checkin.py:352 same-root — list_decided_for_approver, same query
  builder; a senior approver sees the history of what they may decide.
hrms/api/remote_checkin.py:368 same-root — get_pending_count, same query; the
  badge and the list must count the same rows or the badge lies.
hrms/mixins/pwa_notifications.py:125 same-root — the notification addressee is
  the stamped name, which is now chain[0] instead of a department row.
hrms/overrides/employee_checkin_after_insert.py:72 same-root — where the stamp is
  written at filing time; its stale "five tiers" comment corrected with it.

Not affected:
hrms/api/team.py:60 ticket .claude/plans/ticket-approver-chain-consolidation.md
  — the Team TAB gate still lights up for a Department Approver row. Display
  only: every queue behind it fences itself (this commit's included), so it
  shows an empty tab, not another person's data. Left for the consolidation
  ticket rather than widened in a commit about routing.
Leave / Expense / Shift / OT / Attendance Request / Replacement Leave Claim /
  Compensatory Leave Request — already on the shared resolver since cf94549e7
  and 5134f4856; unchanged here and pinned by their own files.

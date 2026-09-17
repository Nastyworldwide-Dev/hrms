# PLAN — an employee can withdraw their own approved request

Owner, 17 Sep 2026: "approved leave or others made by request (the employee)
can be withdrawn and whatever the approved must be reverted back to its
original content, for example, i have 14 days leave balance (annual leave), i
request for 1 day al leave... once approved, deduct... and let say i had to
cancel my leave despite the approved. i withdrawn. it must reflect back to 14
days. this is one of example, and must be applied back to how everything else
is."

Offered three shapes — (a) the employee cancels outright, (b) a withdrawal the
approver confirms, (c) self-service before it starts — he answered:
**"withdrawal. a."**

This REVERSES his own ruling of 14 Sep, recorded in the guard's own docstring:
"The employee who raised it, and anyone else, still cannot."

## What already worked, and what did not

The **reverting** half was complete and is untouched. Every request type undoes
its own work in `on_cancel`: the leave ledger entry (14 back to 14), the
allocated comp-leave days, the replacement leave the OT granted, the Attendance
row, the Shift Assignment.

What was missing was the door — and there were three of them, each keeping its
own copy of "who may cancel":

* `approved_request_guard.cancel_refusal` — the authority;
* `approval.finalize` — re-derived it as `not is_own_request and routed`;
* `frontend/src/utils/cancelRule.js` — returned `false` for the owner, in a
  file whose own comment says it keeps no copy of the rule.

Granting the right in the guard alone would have produced a permission nobody
could reach.

## FLOW

1. `may_cancel(doc, user)` — the routing answer, once: the request's own
   employee, HR, or the person it is routed to.
2. `cancel_refusal` = the money refusals, then `may_cancel`. The owner is
   allowed; two refusals stay and are about money, not roles:
   * paid overtime on a submitted salary slip (refused for everyone, since W5);
   * a request whose days fall inside a submitted salary slip — handing the
     days back while the money stays paid is a hole, so the employee is told to
     ask HR, who can still do it. `REQUEST_PERIOD_FIELDS` names every decidable
     doctype's dates and a test fails if one is missing; a row carrying no
     dates fails CLOSED.
3. `finalize` asks `may_cancel` instead of re-deriving it.
4. `cancelRule.js` returns "approved" for everyone and lets the server answer.

MOCKUP: NOT NEEDED (no new screen or control — the existing Cancel action on
the request sheet stops being hidden from the person it belongs to.)

## EXPECTED OUTPUT

* 14 days, one requested, approved, balance 13. Withdraw: balance 14.
* The same for comp leave days, replacement leave, an Attendance row, a Shift
  Assignment — each already reverses itself.
* A request whose days are in a submitted salary slip: the employee is refused
  with a sentence naming HR; HR and the approver are not.
* Paid overtime: refused for everyone, unchanged.
* Somebody else's request: refused, unchanged.

## Risk

This widens who may cancel, by the owner's explicit instruction. The money
guards above are the deliberate limit. Four tests that pinned the 14 Sep
ruling are AMENDED, each naming the ruling that replaced it, so the change of
policy is on record rather than silently rewritten.

## Pipeline Summary

owner ruling -> this plan -> red tests first (10 new, plus the four amended
suites) -> the four doors -> mapped + neighbour tests -> commit with the family
ledger -> hook-dispatched review -> push -> the owner releases. No schema
change, no patch, no data repair: the next withdrawal is decided by the new
rule, and the reversal that follows it already existed.

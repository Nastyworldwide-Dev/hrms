# Unify request status: one chip, one waiting word, a decision record

APPROVED by the owner, 21 Sep 2026: "proceed as u suggested, make it faster."
The suggestion was the six-slice plan in the Thread F audit reply. Slices 1-4
here; slice 5 (the RequestPolicy table incl. date windows) waits on the owner's
payroll ruling, slice 6 (clocks) is its own change.

## The defect class
Each surface carries its own private copy of "what state is this request in".
`frontend/src/utils/requestStatus.js` was made the one rule on 21 Sep, but two
surfaces never joined it and two states have no colour; and the two doctypes
the fork inherited keep no record of who decided them.

## FLOW (after)
a request is decided
  -> every surface reads requestStatus()          (NEW: RemoteApprovals joins)
  -> a pending row says ONE word, "Waiting"       (NEW: display only)
  -> Employee Issue states carry colour           (NEW: two variants)
  -> Leave / Expense write a Version row          (NEW: track_changes)

## MOCKUP: NOT NEEDED (chip colour and one display word inside an existing component)
No new screen and no new field. The same chips render in the same places; a
pending row's WORD changes from Open/Draft/Pending to Waiting, and the remote
approvals card swaps a hand-rolled span for the standard GStatusChip.

## EXPECTED OUTPUT
  * `requestStatus(dt, {docstatus: 0}).label === "Waiting"` for all seven types,
    and `.pending` stays true. Stored values are untouched: no write path,
    no list filter and no server word changes.
  * `chipVariant("Waiting") === "attention"`; `"In Progress"` -> progress,
    `"Completed"` -> success.
  * `RemoteApprovals.vue` renders `<GStatusChip>`; a Rejected row no longer
    renders identically to a Pending one.
  * `Leave Application` and `Expense Claim` JSONs carry `"track_changes": 1`,
    and a patch clears any Property Setter that shadows it.

## FILES
  frontend/src/utils/requestStatus.js                      WAITING + variants
  frontend/src/utils/__tests__/requestStatus.test.js       pinned
  frontend/src/views/RemoteApprovals.vue                   GStatusChip
  hrms/hr/doctype/leave_application/leave_application.json track_changes
  hrms/hr/doctype/expense_claim/expense_claim.json         track_changes
  hrms/patches/v16_0/track_decisions_on_leave_and_expense.py  NEW
  hrms/tests/test_a_decision_leaves_a_record.py            NEW

## OUT OF SCOPE
  * The RequestPolicy table and the missing date windows (owner ruling).
  * Clock unification and the notification "4 hours ago" bug.
  * Stored status words on the live site: never rewritten here.

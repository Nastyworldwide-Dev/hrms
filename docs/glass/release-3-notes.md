# Release 3 — requests tell the truth

Branch `nz-glass`, commits `ba8ae8c3e..527baf268` (4 commits after the R2 handoff).
Audit: `docs/glass/audit-2026-09-21.md` (sections A, C) + `audit-2026-09-21-requests.md`.
Every `fix:` has a red test on the old code, a fresh verifier pass (two refutations fixed
before landing), and a hook review.

## What changed, in plain words

| # | What | Commit |
|---|---|---|
| 1 | The phone shows a decided request without a reload: the socket never gives up, lists reload on open / wake / pull-down / every update, Replacement Leave and Comp Leave now push their updates too | ba8ae8c3e |
| 2 | "Approved 4 hours ago" the moment it lands is gone: server times are read on the site clock (Dubai), on every phone, in Safari too | ba8ae8c3e, 75e56c451 |
| 3 | An approver can always record a decision: a reject goes through the filing checks (payroll-closed day, day marked Present, changed approver table, missing OT attachment); an approve is still refused with the days named | f04526cea |
| 4 | The employee is told once, on the real decision, with who and when — not on a draft save | f04526cea |
| 5 | Cancelling an OT request / RL claim never silently skips the leave reversal: days already taken refuse the cancel with the reason; a missing allocation is written on the timeline and in the answer | f04526cea |
| 6 | Leave Application and Expense Claim keep a change history (Version) | f04526cea |
| 7 | One status rule on the phone: every list, chip and form reads the same table as the server; a Desk-saved "Approved" on an unsubmitted row shows as pending; Malay colours fixed | 527baf268 |
| 8 | Approve/Reject come from the document's revision, not a whole-doc equality; a local display touch no longer hides them; Expense Claims (child tables) keep them | 527baf268 |

## Not in this release (backlog)

- RL grant dated by the worked day (`ot_date`): collides with the allocation-overlap check when a
  site-today allocation already exists; needs the overlap design first.
- Leave cancel: reverse the ledger instead of deleting it — **owner ruling pending**.
- Expense Claim: show `expense_date` (business) and keep `posting_date` for GL — **owner ruling pending**.
- Typed date in a PWA date box shifts one day west of UTC (frappe-ui DatePicker; patch-package hunk).
- FormView: user-info fetched once; parallel loads (cost items T3).
- AttendanceRequestList field list lacks `status`; get_expense_claims sends no docstatus (inferred).
- Check-in / check-out reminders: plan written, waiting on the four answers.

## Site update notes (Frappe Cloud)

- Migrate: `track_changes` on two doctypes + one patch (clears a Property Setter shadow, idempotent).
- Rebuild the PWA bundle and restart workers (controller hooks changed).

## Post-update checks

1. Approve a request from the approver's phone → the employee's Home shows the new status within
   seconds without a reload; "a few seconds ago" on the notification.
2. Reject a Leave over a day payroll already processed → goes through; approving it still names the days.
3. Cancel an approved OT-to-RL whose leave was taken → refused with the reason; not taken → reversed
   and the request timeline shows nothing extra.
4. Leave Application → menu → View → Version history exists on a fresh edit.
5. Expense Claim review sheet on the approver's phone shows Approve/Reject.

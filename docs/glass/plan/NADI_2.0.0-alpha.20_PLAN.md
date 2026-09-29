# Nadi 2.0.0-alpha.20 — plan

Owner, 29 Sep 2026. Consolidates everything agreed or proposed since alpha.19
shipped. Items marked **OPEN** still need the owner's answer; nothing marked
OPEN is built until answered.

## The direction (what "good" means in Nadi)

1. **Answer first.** The top of every screen answers "what do I need to do now?".
2. **Quiet when nothing's happening.** An empty section is hidden, not shown as "nothing".
3. **Guide, never error.** A problem is explained before any button is pressed (owner, 29 Sep).
4. **One action per screen.** One main button; the rest are rows.
5. **Say what happened.** Every change says who, when and why.

## What ships in alpha.20

### A. Approvals: the chain, fixed (bug, found 29 Sep)
- **Defect:** a reports-to manager is shown Approve on an Expense or Leave whose
  named approver is someone else, then refused: "You can only submit requests
  for yourself." (`validate_staff_approver` accepts only the stored approver;
  the Approvals list and `_is_routed_approver` accept the whole chain.)
- **Fix:** one rule for who may decide = the employee's own approval chain
  (`get_designated_approvers`), limited to **2 levels** (first approver + one
  backup). Both the list and the save use it.
- **Adaptive:** an approver who has **left** (not Active) or is **disabled** is
  skipped, so the next person moves up. An approver **on approved leave stays
  the owner** and keeps being reminded; the backup is told from day 1 that they
  may act.
- **HR setting (Desk):** "Backup approval levels", default 2.
- **Unchanged:** nobody approves their own request; nobody outside the line sees
  it; HR can always approve.

### B. Reminders: the first approver owns it
| When | Who | Message |
|---|---|---|
| Sent | First approver | "Ali sent a leave request" (exists) |
| Next working morning | First approver | One summary: "3 waiting for you, oldest 1 day" |
| Working day 2 | First approver | Summary + "If you can't, the Director can act for you" |
| Working day 3 | Backup + first approver | Backup: "Ali's leave has waited 3 days for Senior." Owner: "The Director has been asked to help." |

- Leave starting soon: the steps run faster (backup told on day 1).
- Working hours only, in the approver's own time zone; no weekends or holidays.
- When someone acts, the other is told who decided.
- Staff see "Waiting on Hafiz · reminded 2×".
- HR sets in Desk: first reminder (1 day), backup after (3 days).

### C. Requests page, less crowded
- **Leave balances, option A:** the two most-used balances as big numbers,
  "All balances ›" opens every type ("6 of 14 left").
- **New request = "+" in the title bar**, top right (iOS pattern). The big lime
  button goes. **OPEN:** owner to confirm "+" (1) vs floating button (2).
- **Short status words:** "Approved · unpaid", "Waiting on Hafiz" — one line.

### D. Home and approvers
- **Home hides empty sections** (no "No new announcements", "Nothing waiting on
  you", "0 days worked" boxes). An empty Home says one line: "All clear today".
- **Approvers:** a count badge on the Requests tab, and a "Needs you" row on
  Requests that opens Approvals directly (today it is More → Your team → Approvals).

## Next release (alpha.21), proposed
- **Undo instead of "Are you sure?"** when withdrawing a request (5 s "Withdrawn · Undo").
- **Guide the person filing** before they send (reuses the approver dry run,
  `approval._approve_would_refuse`).
- **Larger text:** follow the phone's text size setting.

## Still waiting on the owner (not scheduled)
- Roster "Day Type" per entry: which Desk screen the dropdown is on.
- Half-day overtime window: undecided.
- Shift reminders wording/times/opt-out.

## Not doing
- Charts on Home, a floating button, swipe gestures, custom animation, a sixth tab.

## Build order (one reviewed commit per slice)
1. A: chain rule in one place (red test: manager refused today) → list + save agree.
2. A: skip left/disabled; HR setting for levels.
3. B: scheduler job + summary notification + backup notice; HR settings.
4. C: balances A + All balances sheet.
5. C: "+" in the title bar (after the owner's answer).
6. C: short status words.
7. D: Home hides empty sections.
8. D: approver badge + "Needs you" row.
Then iOS gate, design review, alpha.20 bump, release.

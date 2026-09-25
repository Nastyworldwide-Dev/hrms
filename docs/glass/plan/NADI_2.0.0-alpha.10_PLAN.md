# Nadi 2.0.0-alpha.10 — plan (owner "yes, go", 25 Sep 2026)

One release. Every item was agreed item by item; evidence is from the code
and the bench, cited per row. Rule for all of it: measure, find the cause,
fix once at the source, re-measure, lock with a check.

## A. What people see (owner screenshots, 25 Sep)
| # | Defect | Cause (evidence) | Fix |
|---|---|---|---|
| A1 | Anyone can pick their approver ("Goes to") | Leave/Expense/Shift forms show a picker; the server keeps whatever is sent (`leave_application.py:973` only checks one is set) | Read-only "Goes to: <name>"; the server always sets the person's own approver and ignores a sent one |
| A2 | Toast shows an email | `CheckInPanel.vue:1239` passes `req.approver` (the login) | Show the name; toast max 2 lines |
| A3 | Remote check-in sheet is old Frappe style | `RemoteCheckinDialog.vue` raw buttons, lime box, raw textarea | Rebuild on the kit (grouped rows, GTextarea, GButton) |
| A4 | 6 more hand-rolled screens | LateCheckoutDialog, PushNotificationPrompt, SopList, SopFormSheet, HRIssueBoard, SopDetail | Same rebuild |
| A5 | Title twice / "Pull to refresh" at rest | refresher goes `refresher-active` on any small overscroll; mini title fades in | Indicator only past the pull threshold; mini title only once the large one is gone |
| A6 | Bell bigger than avatar | bell 44 px filled circle, avatar 34 px (measured) | Both 34 px circles in a 44 px tap area |
| A7 | Tab icon cut by the active pill | icon top = pill top (measured y 809 = 809) | Centre icon + label in the pill |
| A8 | Page follows the finger at top/bottom | iOS bounce inside ion-content | Contain scroll per page; measured by a drag in WebKit |
| A9 | App says alpha.7 | package.json never bumped | 2.0.0-alpha.10 + changelog for alpha.8–10 |

## B. "Check in again" at 12 am / 3 am (employee report)
Reproduced in WebKit with the real button: IN 09:00 -> "Check in" at 01:01;
IN 08:00 -> "Check in" at 00:01; IN 11:00 -> at 03:00. The phone gives up at
16 h (`CheckInPanel.vue` MAX_OPEN_SHIFT_HOURS, `now.py` MAX_OPEN_SESSION_HOURS)
while the server keeps the session to 06:00 (`remote_checkin.py:427`); and
between 00:00-06:00 past the shift the server stores the tap as asked
(`remote_checkin.py:558`, bench-proven), so a second IN is saved.
- B1 One session rule everywhere: open until 06:00 next morning, or the
  shift's checkout window if later. Phone button, Home timer, server.
- B2 Server: a tap 00:00-06:00 while yesterday's session is open is a
  check-out.
- B3 HR list of days already damaged (two INs, no OUT), found on live data
  after deploy. Nothing changed automatically (no real check-out time is known).

## C. Approved work after the shift counts as OT (owner case, 25 Sep)
Bench: a punch after the checkout window (19:00 on 9-6) has no shift
(off-shift) and off-shift never reaches OT (`ot_calculation.py:1162`).
- C1 An APPROVED remote check-in after the shift takes that day's shift as a
  second session, and counts toward that day's OT.
- C2 It shows in Claim OT ("9 pm – 1 am · 4 h"); paid only when the boss
  approves the claim. Same day rate (normal / off day / holiday), same
  30-minute bands, the day it started (past midnight included).
- C3 A second call-back is its own claim line; a sent claim is never edited.
- C4 Stops where the next shift starts (no double pay).
- C5 From 16 Sep (the current pay period) onward, already-approved after-shift
  sessions become claimable too. Earlier periods and paid days untouched.

## D. Kept as today (owner rulings, 25 Sep)
- Early check-in is not OT (10 Sep rule).
- Work on a leave day is not counted; cancel or shorten the leave first.

## Order (one cause per commit)
B1-B2 -> C1-C5 -> A1-A2 -> A5-A8 -> A3-A4 -> B3 -> A9 -> lock-in checks ->
visual re-baseline -> push. Owner deploys once.

## Lock-in
The `ios` gate gains: approver never choosable, no email in toast text, no
raw button/textarea in components, header controls equal size, tab icon
inside the pill, no content pull past the edges. Backend: tests for each B
and C row above.

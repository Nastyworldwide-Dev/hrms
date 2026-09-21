# Addendum — request dates, types, approval state (21 Sep 2026)

Read-only. Detail with file:line: `audit/2026-09-21/H-request-dates-backend.md` (per-type date
table, downstream table, proof table) and `I-request-dates-pwa.md` (send/display paths, timezone).
Builds on A (transition table). Counts: **Critical 0 · High 4 · Medium 8 · Low 12.**

## The short answer

**Date meanings are NOT mixed in the data model.** Every request type keeps its business date(s) in
their own Date fields (from/to, attendance_date, ot_date, work dates, expense_date); `creation` is
the filing instant; dates cross the API as plain `YYYY-MM-DD` strings and the PWA never converts them.
A request for 24 August stays 24 August in every browser timezone — **with one exception** (below).

**What IS mixed:**

1. **"When was it approved" has no field** on any request type except Remote Checkin Request.
   Leave Application and Expense Claim don't even keep a Version history, and a Leave cancel deletes
   the ledger rows — afterwards nothing says who approved it or when.
2. **Which clock.** Three things are dated on the SITE clock (Dubai) at the approver's tap instead of
   the business date or the employee's clock: the Replacement-Leave grant/reversal (should be dated
   by `ot_date`), the OT filing window, Leave backdating checks. The PWA shows every server timestamp
   as if it were phone-local ("approved 4 hours ago" the moment it lands).
3. **`posting_date` on Expense Claim** is four things at once: filing date, GL posting date, the row
   date the PWA shows, and the payroll-period key — while the real business date (`expense_date` on
   the child rows) never reaches the PWA list.
4. **Typing a date** (not tapping the calendar) into any PWA date box shifts it one day west of UTC —
   a frappe-ui library defect (`new Date("YYYY-MM-DD")`). Safe in Malaysia; wrong for anyone browsing
   from the Americas.

**Downstream effects are type-specific and atomic** — each type's `on_submit`/`on_cancel` writes its own
domain record inside the same save `decide()` runs under the row lock; a failure rolls back the decision.
No generic "approve = do X" branch exists. The silent-failure paths are all on **cancel**: OT/RL balance
reversal can skip or clamp with a log line while `finalize` reports success; Comp Leave cancel can freeze
on the "allocated is mandatory" rule; Attendance Request cancel cancels rows it only relabelled.

**Generic-vs-data:** eight parallel per-type maps (decision field, pending value, summary fields,
withdrawable set — two of them omit Comp Leave), seven copied `on_submit` skeletons, three copies of
"top up or create the allocation". One table would replace them; no new state machinery is needed.

## Findings

### High
| # | Problem | Location | Change | When |
|---|---|---|---|---|
| R-H1 | Leave Application / Expense Claim keep no Version; a Leave cancel deletes the ledger rows → no record of who approved or when | both JSONs (`track_changes` absent); `leave_application.py` cancel | `track_changes: 1` on both (guarded patch); ledger reversal instead of delete is a ruling | R3 (flag) · ruling for the ledger |
| R-H2 | RL grant/reversal and their Leave Period are dated by SITE today at the tap, not by `ot_date` | `ot_request.py:257`, `replacement_leave_claim.py:114`, `hr/utils.py:836` (Comp Leave does it right: `work_end_date+1`) | date the allocation/ledger row by the worked day, as Comp Leave does | R3 |
| R-H3 | PWA shows server timestamps as phone-local ("approved 4 h ago" instantly); Safari sorts Home by `Invalid Date` | `Notifications.vue:97`, `RequestPanel.vue:139-140`, helpdesk/issue lists | parse naive server datetimes as SITE time (dayjs tz plugin, one helper); RequestPanel sort via dayjs (the CheckInPanel fix, not applied here) | R3 |
| R-H4 | Typing a date into any PWA date box → previous day west of UTC | frappe-ui `DatePicker/utils.ts:5-17` via `FormField.vue:147` | patch at source: date-only regex → `new Date(y, m-1, d)`; one TZ-parameterised test | R3 |

### Medium
Expense `posting_date` conflation + `expense_date` missing from the PWA list; PWA seeds `posting_date`
from the phone clock while the server default is site `nowdate()` (they disagree 00:00–04:00 MYT);
OT/RL cancel reversal silent skip/clamp; Comp Leave cancel freeze; AR cancel cancels relabelled rows;
Leave cancel raw-sets docstatus on any On Leave row in range; `notify_approval_status` from `on_update`
for three types (draft Desk save notifies, the later submit does not) and the message carries no time;
late-checkout dialog sends the browser wall clock as a naive string read as site time.

### Low
Site-clock `getdate()` in OT filing window vs employee-clock claimable summary; Leave backdating on site
clock; `bank_month` from `creation`; `posting_date` returned twice and used as list sort; picker opens on
the previous month (LA, on the 1st); "19:56 pm" format; today's holiday reads as past; stale-window keys
on the browser clock.

## What goes where

- **Release 3 (requests)** absorbs R-H1 (track_changes), R-H2, R-H3, R-H4 and the Medium items on
  cancel reversals and notifications — they are the same "requests tell the truth" concern.
- **One request table** (decision field · pending value · business-date field(s) · summary fields ·
  withdrawable · notify-on) replaces the eight maps — inside Release 3, as the refactor its fixes ride on.
- **Rulings:** (a) Leave cancel: reverse the ledger instead of deleting? (b) Expense Claim: show
  `expense_date` (business) and keep `posting_date` for GL only?

## Not a problem (checked)
Date serialisation; Date-vs-Datetime comparisons on the backend (none); calendar-tap dates; the `Today`
button; holidays; attendance calendar navigation; `Date.UTC` in team.js (tz-free arithmetic).

# Two plans, one file (5 Oct 2026)

PLAN A: HR changes a person's shift from a date (blocker, do first)
PLAN B: Approvals filter, bulk approve, table view, announcement (HR request 4 Oct)

Not in this plan: the rostered-punches "Not counted yet" report. Owner, 5 Oct: HR did it, not a bug.
The 3 Oct OT "0 h" stays open until live Shift Type values arrive (see progress.md).

---------------------------------------------------------------------------------------------

## PLAN A: "Change shift from [date]" (HR only)

### WHY
HR cannot change a shift (9-6 to 10-7). Verified on the local site, 5 Oct:
- Cancel the old assignment: refused "linked to Employee Checkin" once any punch exists.
- Edit its shift in place: refused, a submitted assignment keeps only end date, status, Day Type.
- The way that works (end the old one the day before, add the new one) is hidden and two steps.
- Two shifts in one week (Norihsan: Mon-Thu 10-7, Fri 10-4): two open-ended assignments are refused,
  but two weekly schedules (Mon-Thu, Fri) work. Verified: no refusal, dates never overlap.

### FLOW
1. HR opens the person's Shift Assignment (Desk) and presses "Change shift from...".
2. Picks: start date, new shift, and either "every working day" or "pick days per shift"
   (Mon-Thu on one shift, Fri on another).
3. Server (hrms/api/roster.py, one new whitelisted POST, HR roles only, company fence as roster):
   a. Refuse if any day from the start date has a punch or Attendance. Message names the day and
      points to "Fix attendance". Never weakens the existing cancel check.
   b. Assignments that start before the date and run past it: end them the day before
      (end_date is editable after submit, so nothing is cancelled).
   c. Assignments that start on or after the date: no punches (checked in a), so cancel + remove.
   d. Create the new assignment(s) from the date. Open-ended for "every day"; for picked days reuse
      Shift Schedule + Shift Schedule Assignment (repeat_on_days), the existing mechanism.
   e. Switch off any older schedule assignment that would keep creating the old shift.
   f. All in one transaction: any failure leaves the roster exactly as it was.
4. The existing hook re-stamps punches and re-marks days after commit. No new job.

### MOCKUP
Small Desk dialog (date, shift, "every day / pick days", a "what will change" preview list).
Mockup first, owner sign-off, then code.

### EXPECTED OUTPUT
- 9-6 to 10-7 from Mon 12 Oct: old assignment ends Sun 11 Oct, new starts 12 Oct, days before keep 9-6.
- Mon-Thu 10-7 + Fri 10-4 from 12 Oct: Mon-Thu on one shift, Fri on the other, both extend ahead.
- A date with punches or Attendance: refused with the day named; nothing changes.
- A non-HR user, or HR in another company: refused.
- Pressing it twice: second press changes nothing.

### TESTS (red first)
- end-before-date keeps old days; later assignments removed only when punch-free; refusal on a punched day.
- weekday split makes the right shift per weekday; old schedule switched off.
- permission and company fence; transaction rolls back whole on a mid-way error.
- class guard: the cancel check in shift_assignment.py is unchanged.

### OUT OF SCOPE
Supervisors using it (later); changing past days (Fix attendance does that); editing Shift Types.

---------------------------------------------------------------------------------------------

## PLAN B: Approvals filter, bulk approve, table view, announcement

Ask: HR (Afif Rus, 4 Oct) "allow the list to be expanded, filter by request and bulk approve";
owner 5 Oct: no export, banner only, bulk select on phone AND desktop, whichever is best.

### FLOW
1. Approvals page (get_waiting_for_me rows, unchanged): type chips with counts, ageing chip per line
   (amber from 7 days, red from 14), "Select" mode (tick per line, "Select all in this filter"),
   Summary | Table toggle (Table = desktop columns, sort, type filter, search). Summary stays default.
2. Announcement card: "N waiting. Oldest since D. Staff attendance and pay wait on your decision."
   + "Review oldest". Banner only: blocks nothing, nothing mandatory.
3. Sticky bar "Approve N" -> check_many -> sheet "X ready / Y will be refused" with the plain reason
   per refused line -> "Approve X" -> decide_many.
4. Server (hrms/api/approval.py, two new whitelisted POST functions, no new rule):
   - check_many: per item the same read + routed + state gates as get_decision_actions and
     _approve_would_refuse. Read-only (savepoint rolled back).
   - decide_many: per item, own savepoint, calls the existing decide(..., "Approved",
     expected_modified). A failure rolls back that item only, is reported with its reason, loop goes on.
     Batch cap 50 (ceiling: <= 50 row locks per request, upgrade: chunk + queue if HR needs more).
     Approve only: Reject needs a reason each, stays one by one.
   - Access is decide()'s own: nothing is possible in bulk that the approver could not do one by one.
5. Covers the seven DECIDE_THEN_SUBMIT types. Check-in requests (Remote Checkin Request) stay one
   by one: different path. The mockup's confirm sheet shows one; remove it from the mockup.

### MOCKUP
/home/nabil/mockups/mockup-approvals-table.html (A summary, B select + confirm sheet, C desktop table,
D banner only). Fix before build: remove the check-in row from the confirm sheet; the desktop
"Approver line" column is clipped.

### EXPECTED OUTPUT
- 12 ticked, 7 fine, 5 would break: sheet says "7 ready, 5 will be refused" with reasons;
  Approve 7 approves 7; the 5 stay in the list.
- A request that is not theirs: refused as "not yours", the rest go through.
- Already decided: no-op, not an error.
- Employee notifications and ledger entries identical to approving one by one.
- No export. No change to who may approve. Summary stays the default.

### TESTS (red first)
- check_many never writes; decide_many continues past a refused item and a permission failure;
  per-item rollback leaves no half write; over 50 refused; Reject refused.
- frontend: select mode, select-all counts, ageing thresholds, banner text.

### OUT OF SCOPE
Mandatory/blocking approve, export, bulk reject, bulk check-in requests.

---------------------------------------------------------------------------------------------

## ORDER (one root cause per commit)
1. A1 server: change_shift_from + tests.
2. A2 Desk dialog (after mockup sign-off).
3. B1 server: check_many / decide_many + tests.
4. B2 Approvals page: chips, select, banner, table, confirm sheet (after mockup fixes).
Reason: HR is blocked on A today; B is an improvement. Each step ships on its own.

APPROVED: owner, 5 Oct 2026 — "approved" (Plan A shift change first, then Plan B approvals)

# Audit — flows: Home, Calendar, Requests + forms, Approvals (23 Sep 2026)

Branch `nz-glass` @ `e6eb026cb`. Live app: `http://localhost:8080/hrms` (site `fresh.local`, built 01:56 from this tree).
Basis: `2026-09-23-basis.md`. Every finding cites rule IDs from it. Plans checked: `plan/pages/01-calendar.md` (PAGE-1), `02-home.md` (PAGE-2).

**Personas used live**
- Employee: `nurul.aisyah@…` (40 leave applications: 10 Open, 10 Approved, 20 Rejected, all docstatus 0; 1 expense; 2 attendance requests).
- Approver: `nadi.w0.approver@example.invalid` (Leave Approver; 1 open leave from "W0 employee"). Password set at runtime on fresh.local only, never printed.

**Evidence**
- Screenshots: `/tmp/nadi-audit/flows/*.png`
- Raw measures: `/tmp/nadi-audit/flows/results.json`, `run.log`
- Viewports: 390×844, 360×640, 320×640 with root font 200%, 1280×800.

**Site limits (not app defects)**
- The `HR Announcement` doctype is not migrated on fresh.local. `home_announcements` returns 403, so Home shows "Announcements could not be loaded". Announcements were **not checked live**.
- The browser had no geolocation or camera. Camera showed "access denied". The location verdict branches were **code only**.

---

## 1. Coverage

| Area | Screen / sheet / form / action | Status | Note |
|---|---|---|---|
| A | Home (employee, approver) | **live** 390/360/320+200%/1280 | |
| A | NowBar | live + code | |
| A | Check-in button → sheet | **live** 390 | camera denied; time, date, button seen |
| A | Location verdict (inside / far / coarse / no area) | code | no geolocation in headless run |
| A | Confirm → result toast / remote dialog / strict rejection | code | would create a real punch; not fired |
| A | LateCheckoutDialog, RemoteCheckinDialog, StrictRejectionDialog | code | need a stale IN / outside fix |
| A | Offline check-in | **live** 390 | |
| A | NeedsYou (approver) + tap | **live** | |
| A | Announcements block | not checked live | doctype missing on site |
| A | PushNotificationPrompt | code | covered by PAGE-2 §5 |
| B | Calendar page | **live** all viewports | |
| B | Day sheet (no-tap work day, rest day) | **live** 390 | only "not marked" days exist in seed |
| B | Day sheet with punches / OT / team lines | code | no such seed day for either persona |
| B | `?date=` pre-fill (attendance, OT form) | **live** | |
| B | Check-in history list, shift list | **live** 390 | shift form (detail) code only |
| C | Requests page (employee, approver) | **live** all viewports | |
| C | Filter chips (All/Waiting/Approved/Not approved) | **live** | |
| C | Request row → RequestActionSheet (own draft) | **live** | Withdraw + Edit seen |
| C | Back gesture with sheet open | **live** | |
| C | Leave form new | **live** all viewports | balance-after-type not checked (needs a pick) |
| C | Expense form new | **live** all viewports | |
| C | OT form new, Attendance form new, Shift form new | **live** 390 | |
| C | Replacement leave page | **live** 390 | claim form code only |
| C | Leave / Expense dashboards (More) | **live** 390 | |
| C | ListView (leave list) | **live** approver | |
| C | Withdraw confirm | code | not fired (would delete) |
| C | Submit a form end-to-end | not checked | writes real docs; code only |
| D | RequestActionSheet as approver | **live** | |
| D | Reject → confirm | **live** | stopped at "Keep" |
| D | Approve | code | not fired (irreversible) |
| D | RemoteApprovals (empty) | **live** | no pending remote check-ins in seed |
| D | Team dashboard | **live** approver (empty team day) | |
| D | WorkflowActionSheet | code | no workflow on these doctypes here |
| D | `needs_you.py`, `approval.decide` | code | |

---

## 2. Findings

### Critical

| ID | Location | Problem | Why | Expected | Fix | Seen |
|---|---|---|---|---|---|---|
| FLOW-1 | `views/expense_claim/Form.vue:79` `tabs=[{lastField:"taxes"}]` + `FIELDS` allowlist (l.193) · `/expense-claims/new` all viewports | **The new expense claim form has no fields.** Only "Attachments" and "Save" show. The allowlist (commit `94a9e278a`, 22 Sep) dropped `taxes`. `FormView.tabFields` does `findIndex("taxes")` → -1 → `slice(0,0)`: an empty tab. No one can file an expense in the PWA. Screenshot `emp-p390-expNew.png`. | H5, H9, A-3.3.2 (no labels/inputs); live regression | Expense lines, date and approver visible | Set `lastField` to a field that survives the allowlist (`grand_total`), or add `taxes` to `FIELDS`. Add a test that every tab's `lastField` is in the allowlist. | both |
| FLOW-2 | `components/RequestPanel.vue:325` `.splice(0,10)` + `data/*.js limit:10` | **Filter chips and counts are computed over the newest 10 requests only.** Nurul has 43 requests (20 rejected). Chips read "All 10 · Waiting 9 · Approved 1". "Not approved" was **empty** live. "See why it was rejected" is impossible from Requests. | H1, S-FAKE (a count that isn't true), OWN "Not approved lives in Requests" | Chips count the employee's real totals; "Not approved" lists every rejection | Server counts per bucket (`requests_summary` already exists): return counts + one page per chip. Drop the client splice. | both |
| FLOW-3 | `hrms/api/needs_you.py:47-56` ROW_COPY routes + `components/ListView.vue` default tab | **"1 leave request to approve" opens an empty list.** The row goes to `/leave-applications`, which opens on "My leaves": "No leave taken this year". The waiting request sits behind a second tab. Confirmed live (`appr-p390-needsyou-target.png`). | H4, OWN "approvals only where they can be done", OWN "one tap away" | Tap → a list of exactly the waiting items, each decidable | Route every approval row to the new Approvals page (§4B), filtered by type. Until then, pass `?tab=team`. | both |
| FLOW-4 | `RequestActionSheet.vue:112-130` reject; no reason field anywhere | **An approver cannot give a reason when rejecting.** The confirm only says "cannot be undone" (textarea count 0, live). The employee never learns why. PAGE-1 row #5 promises "Claim not approved: {reason}", but no field stores or shows one. | H9, OWN "see why rejected" (task), A-3.3.2 | Reject asks "Why not?" (required) and the employee sees it on the row and in the sheet | Add a reason to `approval.decide` (stored as a comment, or the doctype's remark field). Show it on the rejected row. Mockup 4's "Why not?" sheet is the layout. | both |

### Important

| ID | Location | Problem | Why | Expected | Fix | Seen |
|---|---|---|---|---|---|---|
| FLOW-5 | `CheckInPanel.vue:85-95`; `OfflineBanner.vue` | **Offline, the check-in button still works.** It opens the sheet and camera; the punch fails with a toast. The ruling says: disabled, with "You need signal to check in." | OWN P3/Q8, PWA-OFFLINE, H5 | Button disabled + reason line while `useOnline()` is false | Read `useOnline()` in CheckInPanel; `:disabled` + one line. Add the `offline-writes` gate named in the ruling (it does not exist). | both |
| FLOW-6 | No Approvals page; decisions split across Requests "Team requests" tab, 6 ListView "Team" tabs, RemoteApprovals, Profile row, More row | **Approvals live in five places, with three different decide UIs.** RemoteApprovals asks "Confirm Approve" in its own sheet. RequestActionSheet approves in one tap. ListView rows open the full form. | S-DUP, H4, W-ONE, OWN "approvals only where they can be done, own page" | One Approvals page (§4B), reached from Home "Waiting on you" | Build `/approvals` from `needs_you` + RequestActionSheet. Delete the Team tabs in RequestPanel/ListViews, the More row and the Profile row. | both |
| FLOW-7 | `views/More.vue:78-84`, `views/Profile.vue:270` | Remote approvals has two doors (More for managers, Profile for approvers). More must not hold approvals. | OWN H3, S-DUP | Reached only from Home "Waiting on you" | Delete both rows once FLOW-6 lands | code |
| FLOW-8 | `hrms/api/needs_you.py` + `NeedsYou.vue` | Remote check-ins come from a second endpoint (`pendingCountResource`). Home's rows carry no filter, only a route. "Check-ins outside the area" (PAGE-2) exists only as this separate count. | DRY-ONE, VUE-STATE (two owners of "what waits on me") | One server list of waiting kinds, each with route + filter | Fold `remote_checkin.get_pending_count` into `get_needs_you` | code |
| FLOW-9 | `RequestActionSheet.vue:8-10`, `requestSummaryFields.js` | The request sheet's title is the doctype ("Leave Application", "Attendance Request"). It lists "ID HR-LAP-2026-00044" and "Status Open" beside a "Waiting" chip. | OWN L4 (doctype names never leak), W-ONE, W-PLAIN, H2 | Title in the user's words ("Time off · 15 Sep"); no ID row; one status word | Map doctype → noun (reuse `needs_you.ROW_COPY` nouns); drop `name` and raw `status` from the field lists | live |
| FLOW-10 | `views/leave/Dashboard.vue`, `views/expense_claim/Dashboard.vue`, `ReplacementLeaveCard.vue` | **Leaves and Expenses pages repeat Requests**: balance cards, "Recent" list, create button. The leave balance appears on Requests AND Leaves. The expense total appears on Requests AND Expenses. | S-DUP, OWN "a number lives on ONE page", OWN "balances + money owed belong to Requests" | Requests owns balances, money owed and lists. Leaves and Expenses pages go. | Delete both dashboards and their More rows. Keep `Holidays` (holiday list is its own thing; see §4A). | both |
| FLOW-11 | `views/Requests.vue:27` QuickLinks tile grid (6 tiles) | "Start a request" is a 6-tile grid that pushes the list below the fold (Requests overflows 483 px at 390, 687 px at 360). One tile is HR Issues, which is Helpdesk (More). | S-TILE, L-HICK, S-DUP, OWN compact | One "New request" button opening a type sheet (§4A) | Replace QuickLinks with a GButton + sheet; drop HR Issues | live |
| FLOW-12 | `RequestBalances.vue:170-208` | Requests shows "N day(s) with no attendance · Fix these before payroll". That is the Calendar's "fix" count (PAGE-1 action row). It opens a blank form, not the day. | S-DUP, OWN one place per number, S-EXPLAIN | Lives on Calendar only | Delete the `unmarked` row | code |
| FLOW-13 | `RequestBalances.vue:145-160` | The overtime counter shows hours as `toFixed(2)` ("3.50 hours") and opens the OT form **without** a date. | S-FAKE, OWN C8 (hours as time), A-3.3.7 | "3h 30m overtime to claim" → the claim list in Requests | Use `formatHours`-style h/m; target the claim list (§4A) | code |
| FLOW-14 | `DaySheet.vue:151` `trimSeconds` + `calendar.py:291` `str(timedelta)` | **The day sheet reads "9:00:–18:00".** The server sends "9:00:00" (no leading zero). A fixed `slice(0,5)` keeps the colon. **Missed by PAGE-1** (it plans "Office · 09:00–18:00" but not this bug). | S-FAKE, H2 | "09:00–18:00" | Format on the server (`HH:MM`); drop `trimSeconds` | both |
| FLOW-15 | `DaySheet.vue:47-50` | On a day with no taps, the sheet shows an empty state plus "If you worked, ask for the day to be fixed below", then the button. The sentence restates the button. | S-EXPLAIN (PAGE-1 D10 covers the button, not the sentence) | Button only, or none | Cut the body text in the rebuild | live |
| FLOW-16 | PAGE-1 §3 action row "● 3h 30m overtime to claim ›" | **Plan conflict, missed by PAGE-1.** The owner rule says claims belong to Requests and the Calendar only *shows* claimable days. The action row repeats the number that the Requests overtime row holds. | S-DUP, OWN "claims belong to Requests" | Calendar keeps the dot + day-sheet claim; the total lives in Requests | Amend PAGE-1: drop the overtime action row; keep "N days need a fix" | code |
| FLOW-17 | `ListView.vue:156-177` Team tab filter | The "Team" tabs on list pages filter only `employee != me`, not "routed to me". An approver sees whatever the doctype permission allows, including decided rows of others. | H4, OWN "actionable only" | Only rows waiting on this approver (the `_is_routed_approver` fence) | Delete the Team tabs (FLOW-6) | code |
| FLOW-18 | `CheckInPanel.vue:3-14, 86-95, 176-182` | Check-in sheet: eyebrow "CHECK IN" in caps; title-case "Check In" / "Confirm Check In"; trailing arrow on a non-navigating button; a date line under the time. Covered by PAGE-2 (H3/H8, S-ARROW, §4). Listed only to confirm it is live: `emp-p390-offline-tap.png`. | PAGE-2 | as PAGE-2 | as PAGE-2 | live |
| FLOW-19 | `GStatusChip` + `.g-eyebrow` (global) | Status chips render in caps ("WAITING", "APPROVED & UNPAID"). Every section has a caps eyebrow ("START A REQUEST", "REQUESTS", "WAITING ON SOMEONE"). Form labels too ("LEAVE TYPE", "FROM DATE"). | W-CASE, W-DYS, NG-CAPS, S-EYEBROW | Sentence case | Remove `text-transform: uppercase` from chip and eyebrow tokens (one place each) | live |
| FLOW-20 | `leave/Form.vue`, `ShiftRequestForm.vue` | Forms ask the employee to pick their own approver ("Leave approver", "Approver"). The server already knows it. Titles are doctype names ("New Leave Application", "New OT Request"). | A-3.3.7, H2, OWN L4 | "Goes to Hafiz" as one line; the title in plain words ("Ask for time off", "Claim overtime") | Make the approver read-only text when the server resolves one | live |
| FLOW-21 | `views/RemoteApprovals.vue:128-141, 178-180, 262` | IN/OUT shown raw; "No reason provided." in italics; "Confirm Approve" / "Remote Approvals" in title case; the card for the employee name uses `truncate`. | OWN C9, W-DYS, W-CASE, A-1.4.10 | "Check in 09:12"; plain text; sentence case; wrap | Reuse the Calendar punch wording; drop italic and truncate | code |
| FLOW-22 | `RequestPanel.vue:210` History tab | History covers leave, expense and shift only (the comment says so). OT, attendance and replacement leave decisions vanish once decided. | H1, H4 | Decided-by-me for every type | Moves to the Approvals page "Decided" view, server-side | code |

### Polish

| ID | Location | Problem | Why | Expected | Fix | Seen |
|---|---|---|---|---|---|---|
| FLOW-23 | `RequestActionSheet.vue:385-399` | Toasts say "Approved successfully!", "Document submitted successfully!". | W-PLAIN, OWN L4 ("Document") | "Approved. W0 employee is told." | Plain copy | code |
| FLOW-24 | `RequestActionSheet.vue:12-17` + Edit button | Two doors to the same form in one sheet (header external-link icon + "Edit"). The icon has no name. | S-DUP, A-1.1.1 | One "Edit" | Drop the icon | live |
| FLOW-25 | `RequestBalances.vue:45` | Balance card note "of 16" under "16 · PRIVILEGE LEAVE": repeats the number when nothing is used. | H8 | Show "of N" only when used > 0 | One condition | live |
| FLOW-26 | `SideNav` at 1280 | Own name clipped with an ellipsis ("Nurul Aisyah binti…"). | A-1.4.10, HIG-TYPE | wraps | drop `truncate` | live |
| FLOW-27 | `LateCheckoutDialog.vue` | "Actual Check-Out Time" title case; "Pending approval from your reporting manager." doesn't name them. | W-CASE, H1 | "When did you leave?"; "Goes to {name}" | copy | code |
| FLOW-28 | `ReplacementLeave.vue` | A separate "Overtime bank" page holds a balance (0 h) that also belongs to Requests balances. | S-DUP | One row in the balance breakdown | Fold in (§4A) | live |
| FLOW-29 | `views/attendance/EmployeeCheckinList.vue` at 390 | Empty-state body "Punch in from Home…" uses "punch", not "check in". | W-ONE | "Check in from Home…" | copy | live |

### What the approved plans missed (summary)
- PAGE-1: FLOW-14 (shift time "9:00:"), FLOW-15 (explaining line), FLOW-16 (overtime action row duplicates Requests).
- PAGE-2: FLOW-3 (a Home row landing on an empty list: its "each row opens the place, filtered" needs a place that exists), FLOW-5 (offline check-in not blocked), FLOW-8 (two sources for "waiting on you").
- Both plans are otherwise confirmed live: D2 pre-fill is broken (inputs empty with `?date=2026-09-08`), D10 always-on fix button, D12 raw IN/OUT (code), H1 RequestPanel on Home, H2/H3 caps date, H4 greeting with emoji.

### Mockup 4 against the basis (layout + language only)
- "Good morning, Nabil" greeting → S-HERO, OWN H7. Don't copy.
- "Extra hours" / "clock in" → OWN L2 / PAGE-2 §6. Use Overtime / check in.
- "Not approve" button vs the ruled "Reject" (R4) and the chip "Not approved" → W-ONE. Pick one; the chip word "Not approved" can stay as a *state*, the *action* is "Reject".
- The New request sheet lists "Plan a work trip", "Join training", "Things you hold": none exist → S-FAKE, YAGNI.
- More holds "Your team" and "Payslips" → owner: no payslips yet.
- **Keep from it:** the Approvals layout (count + oldest age, one card per request, cover conflict line, balance-after line, decide in place, "Approve the N with no conflicts"), the "Why not?" reject sheet, and the "This goes to Hafiz. You can take it back any time before he decides" form footer.

---

## 3. Keep list (works, don't touch)
- Check-in guards: 60 s duplicate lock, `client_tap_id` replay, server-stamped time, committed action held while the sheet is open (`CheckInPanel.vue:960-1040, 509-528`).
- Location verdict in words, not a map (`CheckInPanel.vue:124-140, 800-930`).
- NowBar: always renders, server-decided state, ticks per minute.
- `needs_you` counts through the same `_is_routed_approver` as `decide()`. The fence is right; only its destination is wrong (FLOW-3).
- `approval.decide`: row lock, `expected_modified`, atomic decide + submit.
- Reject/cancel confirm; approve in one tap (`RequestActionSheet.vue:285-300`).
- Withdraw + Edit on your own draft (live).
- "Waiting on someone" / "Finished" piles and the "with Hafiz since Monday" line (R1, R2).
- RequestBalances: a failed read shows an error, not zero.
- The day sheet shows leave **type**, never reason (`DaySheet.vue:118`; `team.py`) — matches OWN A3.
- The offline banner itself (not dismissible, plain words).
- Back with a sheet open: the sheet closed and nothing stuck (live, request sheet). Note: Back also left the page (went to Home). PAGE-0 wants Back to close the sheet *and stay*.

---

## 4. Page contents

### 4A. Requests

**Job:** "What have I asked for, what do I have left, and what am I owed?"

**Height target:** fits 390×844 with 2 balances + 5 rows. 360×640 scrolls only the list.

| # | Item | Verdict | Rule |
|---|---|---|---|
| 1 | Header "Requests" | keep | A-2.4.6 |
| 2 | **Balances strip**: up to 3 used leave types, one line each: `Annual leave · 7.5 left`. "All balances ›" opens the breakdown sheet | change (from 4 big cards + "Show N more") | OWN balances belong here, S-CARD, OWN compact |
| 3 | **Money owed** row: `RM 248.00 approved, not paid yet ›` → the list filtered to those claims | keep, one row | OWN money owed belongs here |
| 4 | **Overtime to claim** row: `3h 30m overtime to claim ›` → the claim list (days with claimable overtime, each "Claim") | change (h/m, target) | OWN claims belong to Requests, OWN C8, FLOW-13 |
| 5 | "N days with no attendance" row | **cut — lives on Calendar** | FLOW-12, S-DUP |
| 6 | **One "New request" button** → type sheet | change (replaces the 6-tile grid) | S-TILE, L-FITTS |
| 7 | Filter chips All / Waiting / Approved / Not approved, **server counts** | change | FLOW-2, R3 |
| 8 | Two piles "Waiting on someone" / "Finished"; row = what · when · with whom since when · chip | keep | R1, R2 |
| 9 | Rejected row shows the reason in one line | change (new) | FLOW-4, H9 |
| 10 | "Show N more" | keep | NG-PD |
| 11 | "My / Team / History" segmented control | **cut — lives on Approvals** | FLOW-6, OWN approvals only where done |
| 12 | "HR Issues" tile | **cut — lives on More (Helpdesk)** | S-DUP |
| 13 | Row → request sheet: title in plain words, dates, days, **your reason**, **their reason if rejected**, who decides; actions Withdraw (waiting, own) or Cancel (approved, when allowed) | change | FLOW-9, OWN L4 |
| 14 | Leaves page, Expenses page, Replacement leave page | **cut — content folds into rows 2–4 and the sheets below** | FLOW-10, FLOW-28 |
| 15 | Holidays list | **move to Calendar** (the sheet names the holiday; "Public holidays" link stays under More if the owner wants the year list) | OWN one job per page |

**New request type sheet** (one tap from row 6):
- Time off → leave form (the type is picked **in** the form; the balance for that type shows beside it)
- Overtime → the claim list (row 4), not a blank form
- Expense → expense form
- Fix a day → **opens Calendar** (the fix starts from the day; rule: one place, PAGE-1)
- Change a shift → shift request form
- Cut: HR issue (lives on Helpdesk), trips, training, assets (don't exist).
- Rule: L-HICK (5 → 4 choices), OWN one place per action.

**Balance breakdown sheet** (from "All balances ›"):
- One row per leave type: `Annual leave — 12 given · 4.5 taken · 7.5 left`, expiring date when set.
- Replacement leave: `Overtime bank — 6 h (0.5 day)`, with "Use it" → leave form with the type set.
- No bars, no cards. One list. Rule: S-CARD, S-STAT (every row leads to "use it" or is informational only on demand), NG-PD.

### 4B. Approvals (new page, `/approvals`)

**Job:** "What is waiting on my decision, and let me decide it here."
**Reached from:** Home "Waiting on you" rows only (PAGE-2). Not in More, not in Profile, not a tab.

| # | Item | Verdict | Rule |
|---|---|---|---|
| 1 | Header "Approvals" | new | A-2.4.6 |
| 2 | Summary line: `4 waiting · oldest 3 days` | new (from mockup 4) | H1 |
| 3 | Type chips (only types with rows): Time off · Overtime · Fix a day · Expense · Shift · Check-ins outside the area. Home's row opens this with its chip set | new | NG-PD, FLOW-3 |
| 4 | One card per request: who · what · when · **their reason** · balance after (time off) · cover line ("2 others in Service already off Monday": names + leave **type** only) | new | OWN A3 (type, never reason of others), H6 |
| 5 | Approve / Reject **on the card** (48 px). Reject opens "Why not?" (required). Approve is one tap (no undo: `decide` submits, so the toast just confirms) | new | OWN one tap, FLOW-4, L-FITTS |
| 6 | Remote check-ins: same card; shows distance + photo; approve/reject in place | move from RemoteApprovals | FLOW-6, DRY-ONE |
| 7 | "Approve the N with no conflicts" | new (mockup 4), only when N ≥ 2 | H7 |
| 8 | "Decided by you" (last 30 days, all types) | move from Requests History + RemoteApprovals History | FLOW-22 |
| 9 | Empty: "Nothing waiting on you." + nothing else | new | NG-EMPTY (no action exists) |
| 10 | Requests "Team requests" tab, ListView "Team" tabs, RemoteApprovals page, More row, Profile row | **cut — all live here** | S-DUP, OWN |
| 11 | Team dashboard (who is in/off) | **not here — stays on Team** (a view, not a decision) | OWN one job |

Server: `needs_you.get_needs_you` gains the remote check-in kind (FLOW-8) and returns the rows, not only counts. Decide reuses `approval.decide` + a `reason` param.

### 4C. Amendments to approved plans
- **PAGE-1 §3:** drop "● Xh overtime to claim" action row (FLOW-16). Add: shift time formatted by the server (FLOW-14). Day-sheet empty state has no explaining line (FLOW-15). Holidays list moves here (4A #15) only as the day sheet's holiday name, which PAGE-1 already has; no new list.
- **PAGE-2 §3:** "Waiting on you" approval rows open `/approvals?type=…` (FLOW-3). Remote check-ins come from the same server list (FLOW-8). Add: check-in button disabled offline with "You need signal to check in." (FLOW-5).

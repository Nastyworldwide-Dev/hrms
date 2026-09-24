# Nadi — every screen, its job, and how it must look (alpha.6)

Rules referenced by ID are in `alpha6-standard.md`. "Today" = measured on the live build 24 Sep 2026, 390 px phone
(`frontend/e2e/alpha6-audit.mjs` → `/tmp/alpha6/shots/audit.jsonl`, plus your 9 screenshots).

Legend: **Must show** is in priority order, top first. **Primary** is the one filled button (B1).

---

## A. Tab roots (large title, tab bar visible)

### A1 Home
- **Purpose:** check in or out, and see if anything needs me today.
- **Must show:** date · my state today (checked in since… / not in / off today) · my shift today · **Check in/out** · anything waiting on me (one row each) · news (only if there is any) · this week in one group.
- **Primary:** Check in / Check out.
- **Empty:** no news means the News group is hidden, not "No news." (R7: a line that says nothing is noise).
- **Today, broken:**
  - "No shift today" when the person has a default shift (bug, `api/now.py:65`).
  - The large title is missing (the logo sits where the title goes) (T7).
  - "Announcements" and "Your week" headings are lime (G6).
  - "No news." shown.
  - Weights at 800 (T2).
  - A 10 px tab label (T1).

### A2 Calendar
- **Purpose:** see what happened on any day, and fix it.
- **Must show:** month grid · legend · tap a day to open the day sheet (what happened, and Fix / Ask for time off).
- **Secondary:** All check-ins, Your shifts (as list rows, not underlined links).
- **Today, broken:**
  - "All check-ins" and "Your shifts" are underlined web links under 44 px tall (L4, R3).
  - The grid sits in a glass-looking card with a rim. It should be a plain content group (G1).
  - Nine legend items across two lines (cognitive load; the legend should show only the states used this month).

### A3 Requests
- **Purpose:** ask for something, and see where my asks are.
- **Must show:** New request (primary) · balances in one line · Needs you (rows) · Recent (5, then Show all).
- **New request sheet (S6):** grouped rows, each with icon, title and one-line hint:
  - Time off: "Days away, sick or holiday"
  - Overtime: "Get paid for extra hours"
  - Expense: "Get money back for something you paid"
  - Shift change: "Work a different shift"
  - Fix a day: "A missing or wrong check-in"
- **Today, broken:**
  - The sheet is 5 bare words with no separators (your screenshot).
  - Headings are lime (G6).
  - Status chips are filled green (G5, G6).

### A4 Score
- **Purpose:** my review score and goals.
- **Empty:** one group, "No review yet", with a footer "HR opens reviews; you'll get a notification."
- **Today, broken:**
  - The empty state is a card with a lime left stripe (G6, a web "alert" pattern, not iOS).
  - Weight 800.

### A5 More
- **Purpose:** everything that is not daily.
- **Must show:** one grouped list: Help, Who to ask, Announcements, SOPs, Public holidays, then **You** (profile) at the top as an iOS "account" row with avatar and name.
- **Today, broken:**
  - The list is drawn as a glass-rimmed card (G1).
  - The avatar button in the header duplicates the You row (N4).

## B. Pushed screens (back chevron, inline title)

### B1 You (Profile + Settings)
- **Purpose:** who I am, and how the app behaves for me.
- **Layout (iOS Settings pattern, K2/R1):**
  - Header: avatar, name (Title 3), role · place (Subhead, secondary).
  - Group "Work": Manager (value) · Shift (value) · Your details ›
  - Group "App": Appearance (menu: Light / Dark / Automatic) · Notifications [switch, trailing] · Reminders [switch, trailing]. Footer: "Reminders nudge you if you forget to check in or out."
  - Group: Change password ›
  - Group: **Log out** (red text, centred row, confirms) (B3).
  - Footer: version.
- **Today, broken (your screenshot):**
  - Switches on the left and outside a group (K-table, TOG).
  - Hint text floats (R4).
  - The theme is a 3-segment control; iOS uses a menu row "Appearance" (PICK).
  - Log out is a bordered button, not a destructive row (B3).
  - The name is weight 800 (T2).

### B2 Notifications
- **Purpose:** what changed for me.
- **Must show:** Today / Yesterday / Earlier groups · each row: icon, one line of what happened, who · when · unread dot.
- **Actions:** Mark all read (plain text button in the bar, right) · tap a row to open the thing.
- **Today, broken:**
  - 30 rows in one endless list (R6). Show the newest 20, then "Show earlier".
  - "Earlier" heading is lime (G6).
  - "30 unread" repeats the badge.

### B3 Help
- **Purpose:** get a problem fixed.
- **Must show:** Open issues (rows) · Report a problem (primary) · Who to ask ›.
- **Today, broken:**
  - The "OPEN" header is all-caps lime (T6, G6).
  - Status "Open" chips are outlined orange boxes beside a chevron; they should be secondary text (R2).

### B4 Who to ask / B5 Change password / B6 Approvals / B7 Team / B8 SOPs / B9 Announcements
- Same list anatomy (R1–R4). Headers Footnote grey. One primary at most.
- **Approvals:** each request is a row (who · what · when). Tap opens the approval sheet with **Decline** (left) and **Approve** (right, primary). Managers see leave TYPE, never the reason (standing ruling).

### B10 Time off overview ("Leave and holidays") and B11 Expenses overview
- **Purpose:** my balance / money at a glance, and the way to ask.
- **Today, broken (screenshot):**
  - The expense total is a **lime-filled card**, and the primary "Claim an expense" is also lime. Two tinted things (G5).
  - Balances use 800 weight and lime bars (G6).
  - "View list" and "View leave history" are underlined web links (R3).
  - "Casual Leave · 0d · with Administrator · a month ago" is three facts of noise per row.
  - The page title "Leave and holidays" (18 chars) breaks T8.
- **To:**
  - One group of balances as rows: "Annual   6 days left".
  - Primary: Ask for time off.
  - Recent: 5 rows, then Show all ›.

### B12 Lists: Your time off, Your expenses, Your overtime, Your shift changes, Your day fixes
- Rows: what (Body) · dates (Subhead) · status (secondary word, colour dot). Grouped by month. The newest 20, then Show more.

## C. Forms (pushed screens, grouped-list form, K2)

Shared shape for every request form:

```
‹  Time off                         (title ≤15)
┌ Kind of leave        Annual  ⌃⌄ ┐   ← menu row (PICK)
└──────────────────────────────────┘
┌ From              Thu 24 Sep    ┐   ← compact date rows
│ To                Fri 25 Sep    │
│ Half day                   [ ○] │   ← switch row
└──────────────────────────────────┘
  2 days · 6 left after this          ← group footer (R4)
┌ Note for Hafiz (optional)        ┐   ← text view group
└──────────────────────────────────┘
┌ Add a file                    ›  ┐
└──────────────────────────────────┘
[        Send to Hafiz           ]   ← the one primary (B1, B4)
```

- **No** section headings for single groups. **No** empty sections (F).
- **No** approver field when there is exactly one approver: it becomes the button ("Send to Hafiz"). It shows as a menu row only when there is a real choice. Names only (K3).
- Fields hidden from employees: posting date, company, employee, department, status, series, currency, accounting anything.

| Form | Rows (in order) | Primary |
|---|---|---|
| **Time off** | Kind of leave · From · To · Half day (+ which day) · footer "N days · M left" · Note (optional) · File | Send to {name} |
| **Overtime** | Day worked (menu of open days, newest first, shows hours) · Hours (prefilled, editable) · What was the work? · footer "Paid as overtime" | Claim {1h 30m} |
| **Expense** | Items group: each row "Taxi · Mon 21 Sep · RM 45.00" + "Add an item" · footer Total · Receipt(s) | Send to {name} |
| **Shift change** | New shift (menu) · From · To (optional, footer "Leave empty for one day") | Send to {name} |
| **Fix a day** | Day · What happened (menu: forgot to check in / out, worked from home, on duty) · In time · Out time · Note | Send to {name} |
| **Report a problem** | What about (menu) · How urgent (menu) · What happened (text) · File | Send to HR |

**Today, broken (screenshots + audit):**
- Every field is a square, empty, full-width box with a label above: the web-form look (K1, K2). Measured: fields 48 px with **0 radius** (forced by `FormView.vue:1023`); link pickers 44 px with 12 px radius. Two looks on one form.
- Expense shows 9 headings, 6 of them empty (F). Posting date shows (W1).
- Overtime lists every past day as a card: open, claimed, unclaimable (R6).
- Approver shows an email (K3, W10).
- "Save" on every request (B4).
- Lime section headings (G6).
- Half day is a 20 px checkbox (K-table, L4).
- **Time off drags sideways on iPhone:** WebKit sizes a native date input from its own content and ignores `width:100%` unless `appearance:none` and `min-width:0` are set. Chrome cannot show this (L1).

## D. Sheets

| Sheet | Bar | Content | Today |
|---|---|---|---|
| New request | × left, title | S6 rows (icon + title + hint) | bare words, no separators |
| Day (Calendar) | × left, date title | what happened (rows), then the action for that day | OK. Check that the action is one primary |
| Approval | × left, title | who · what · when · note; **Decline / Approve** | check |
| Check-in / check-out | × left | map/location line, then the one action | check |
| Public holidays | × left | month-grouped rows, Next marked | OK |
| Your details | × left | grouped read-only rows | check |
| Link search (pick a person/type) | × left, search field | rows with ✓ on the chosen | check |

All sheets: one kind (GModal), grabber, swipe-to-close with "Discard changes?" when typed (S3).

## E. Chrome (every screen)

- **Top bar:** no background or hairline; content scrolls under it with a fade (G4).
  - Left: back chevron (pushed screens only).
  - Right: at most the bell. The avatar button goes, because You lives in More (N4, B7: max three groups).
- **Tab bar:** labels 11 pt (T1, currently 10 px). Selected = tint, others = secondary.
- **Desktop:** sidebar, one 720 px column. Same rules.

---

## F. Measured violations, whole app (24 Sep 2026)

`frontend/e2e/alpha6-audit.mjs`: 41 screens × (staff + approver) × (phone dark, phone light, desktop) = **197 views**, 0 load errors, 0 page errors.

| Rule | What the audit found | Screens |
|---|---|---|
| T1 type ramp | Sizes off Apple's ramp in use: **10, 14, 18, 19, 23, 29, 40, 13.5 px** | 41 of 41 |
| T4 min 11 | Tab bar labels are **10 px** | every tab-bar screen |
| T2 weights | Weight **800** (Heavy) on titles, buttons, numbers; also 420 | 41 of 41 |
| G6 tint as decoration | Lime used on headings and labels | 21 screens |
| G5 one tint | Two lime-filled things (Expenses total card + button) | Expenses overview |
| K1 one control look | **6** different field looks: 48/0, 49/0, 64/0, 44/12, 48/12, 50/12 (height px / radius) | every form |
| L8 radius set | 8 radii in use: 2.5, 8, 12, 16, 20, 24, 50%, 9999 | — |
| B buttons | **8** different button heights: 41, 44, 48, 50, 51, 52, 56, 61 | — |
| L4 44 px target | "Menu", "View list", "All check-ins", "Your shifts", "View leave history" | 8 screens |
| B4 verbs | "Save" on requests | 7 forms |
| F empty sections | 6 empty headings on New expense, 4 on the expense detail, "Other details" on time off | 3 forms |
| K-table checkbox | Checkbox used as an on/off | 5 forms |
| T8 title ≤15 | "Leave and holidays", "Your shift changes" | 2 |
| W1 jargon | Employee, Employee name, Explanation, Shift type, Approver, Expense approver, Leave approver, Advance payments, Exchange gain/loss, Accounting details/dimensions, Posting date, Sanctioned, Total amount reimbursed, Leave type, You claim, OT date, Claimed hours, "once submitted", "Your applications", "documents" | 20+ strings |
| L1 sideways | 0 in Chrome. **WebKit-only** date-input bug (see C) | Time off, and any form with a date |
| G1 glass on content | 0 (alpha.5 held) | — |
| P2–P3 native feel | No tap-highlight reset, no `user-select` on chrome, no `overscroll-behavior` anywhere in the theme | app-wide |

# Nadi 2.0.0-alpha.5 — the whole app, one design, no residue

Status: **PROPOSAL, waiting for Nabil's go.** 23 Sep 2026, branch `nz-glass`.
Nothing in this file has been built. No code changed.

Owner ask (23 Sep): "alpha 5 to truly cover the entire app, no more gaps, no
more old residue… evaluate against what i asked for and propose a better design
that truly match glassmorphism… basis and evidence… change, adjust, delete,
reorder, refine, remove, anything. and why."

How this was made: 9 owner screenshots (Home, Calendar, Requests, Score, More,
Help ×2, HR Contacts, Public holidays, Notifications), a read-only audit of all
38 views, a diagnosis of the two data bugs, and an evidence pack from Apple HIG
(fetched text), WWDC25, NN/g, WCAG 2.2, MDN and Baymard. Every "why" below
points at one of those, or at an owner ruling already on record in
`docs/glass/audit/2026-09-23-recollection-rulings.md`.

---

## 0. The three root causes (everything else is a symptom)

| # | Root cause | Symptoms it produced |
|---|---|---|
| RC1 | **Screens outside the five tabs never got the Glass shell.** Each draws its own `<header>` with a `border-b-2` hairline and no bell/avatar — the old Frappe look. | HR Contacts, Notifications, Profile, Change password, all 7 list screens, all forms, SOP detail, ticket detail/new |
| RC2 | **Glass is on the content, not on the chrome** — the opposite of Apple's rule. `.g-glass` (every content card) carries `backdrop-filter: blur(20px)` (`glass-components.css:259-263`); the header and sheets carry none. Owner ruling D3 (10 Sep, affirmed 22 Sep) and D4 (blobs out, 23 Sep) were never built. | Muddy tab bar over cards, "lighter card" inside the holiday sheet (glass on glass), cards whose contrast shifts with scroll |
| RC3 | **Three readers count "worked" three different ways, and nobody named the day.** Calendar colour = Attendance only (`AttendanceCalendar.vue:113`, `hrms/api/__init__.py:362-385`); the orange dot and "no attendance" count = punches minus Attendance **including today** (`calendar.py:283`, `requests_summary.py:162`); Home = Attendance + paired punches (`home.py:43-62`). | Today looks "not present"; "1 day with no attendance" is today (a false alarm) and never says which day |

Plus one plain bug: **the PWA never receives the site's time zone** (`hrms/www/hrms.py:get_boot` sends none), so `siteTime` always falls back to hard-coded `Asia/Dubai` (`utils/siteTime.js:15`). The site runs on Malaysia time (UTC+8), 4 hours ahead of Dubai. So "Approved … 18:31" is read as 22:31, and at 21:34 it says **"in an hour"** — that matches the screenshot exactly.

---

## 1. Evidence used (short form)

| Key | Rule | Source |
|---|---|---|
| E1 | "Liquid Glass forms a distinct functional layer for controls and navigation… Don't use Liquid Glass in the content layer." | Apple HIG, Materials — developer.apple.com/design/human-interface-guidelines/materials |
| E2 | "Always avoid glass on glass." | WWDC25 session 219, "Get to know the new design system" |
| E3 | Tab bar floats; content peeks through. Use a **scroll edge effect** under floating bars, one per view, not decorative; content stays inside the safe area. | HIG Tab bars; HIG Scroll views; HIG Layout |
| E4 | Sheets: medium/large detents, grabber, **title in the sheet's top bar with Close on the trailing edge**; a title-like text alone in the top-leading corner confuses dismissal. | HIG Sheets; HIG Toolbars |
| E5 | Notifications: "Prefer brief titles that people can read at a glance… succinct". Feed item = who + what, time, one-line preview, no raw IDs. | HIG Notifications; Microsoft Teams activity-feed design |
| E6 | Show a few first; progressive disclosure improves learnability, efficiency, error rate. Load-more raises interaction cost; endless scroll hides the end. | NN/g Progressive Disclosure; NN/g Infinite Scrolling |
| E7 | Empty states explain why and give the next step. | NN/g Empty States; HIG Tab bars |
| E8 | Segmented control ≤ ~5 segments; use a tab bar for separate sections. | HIG Segmented controls; NN/g Tabs Used Right |
| E9 | Visibility of system status — always tell people what is going on. | NN/g Heuristic #1 |
| E10 | Cognitive load; plain language; 50–75 characters per line. | NN/g Minimize Cognitive Load; HIG Writing; Baymard line length |
| E11 | 44×44 pt targets; 4.5:1 text contrast; text over busy backgrounds fails (WCAG F83). | HIG Buttons/Accessibility; WCAG 2.2 SC 1.4.3, 2.5.8 |
| E12 | Honour Reduce Transparency / Reduce Motion (ship a solid fallback — the media query is not Baseline). | MDN prefers-reduced-transparency / -motion |
| E13 | One consistent navigation bar; large title shrinks on scroll; title under 15 characters. | HIG Toolbars |
| E14 | One or two prominent buttons per view; destructive never primary. | HIG Buttons |
| E15 | Dates follow the region; relative time for recent activity. | HIG Inclusion; MDN Intl.RelativeTimeFormat |

Weak spots, said plainly: grouping a feed into Today / Yesterday / Earlier is an
industry pattern (iOS, Gmail, Teams all do it), not a written guideline. There
is no official cap on filter chips. The Material 3 pages could only be read
from search snippets.

---

## 2. What changes — app-wide (applies to every screen)

### W1. One shell for every screen  (fixes RC1)
- **Change:** every route renders `BaseLayout` + `GAppHeader`. Tab roots show the Nadi mark + title; pushed screens show Back + title. The right side is the **same everywhere**: bell + avatar. On Notifications, the bell becomes "Mark all read", so a screen never points at itself.
- **Delete:** the hand-drawn headers in HRContacts, Notifications, Profile, ChangePassword, ListView (7 lists), FormView (all forms), SopDetail, SopFormSheet, TicketDetail, TicketNew. Delete the Refresh button on HR Contacts too — pull to refresh already does that job.
- **Why:** E13. The owner's "looks like old Frappe" is exactly these headers.
- **Lock:** a gate test. Every route component resolves to BaseLayout, and no view contains `<header` or `border-b-2`.

### W2. Glass where Apple puts it: chrome only  (fixes RC2; builds rulings D3 + D4)
- **Glass (blur + rim):** the tab bar, desktop side nav, app header (when content scrolls under it), sheets and their scrim, toasts.
- **Solid:** every content card, list panel and row. `.g-glass` keeps its rim, radius and lift but loses `backdrop-filter`. It uses the solid fallback fill that §6.1 already defines. So layout does not move and the "look" stays. Only the see-through frost on content goes.
- **Delete:** the three light-field blobs (`GLightField`, `.g-lightfield*`, `field.*` tokens). Owner ruling D4, 23 Sep.
- **Add:** a **scroll-edge fade** under the floating tab bar and under the header: a short gradient from the page ground to transparent. Rows then fade out before they pass under the glass, instead of showing through it.
- **Why:** E1, E2, E3, E11 (WCAG F83). The owner's "untidy under the bottom bar" on Help is rows showing through a 56% glass bar with no edge effect.
- **Lock:** a gate test. `backdrop-filter` is only allowed on the chrome selectors list; anything else fails the build.

### W3. One row, one button, one time
- **One row:** 9 components draw their own rows or cards (ContactCard, RequestList + items, ExpenseItems, ProfileInfoModal, RequestActionSheet, HRIssueBoard, SopList, TeamDashboard, KpiDetail). Each moves onto `GListRow`: title on one line, one short second line, a status tag on the right.
- **One button:** remove every leftover frappe-ui `Button`, `Switch` and `Badge` (10 components). Use `GButton`, `GSwitch` and `GTag` instead.
- **One time:** the boot sends the site time zone, so `siteTime` stops guessing Dubai. The 6 lists that still call raw `dayjs(x)` move to `siteTime`.
- **Why:** consistency (owner: "inconsistency"), E15, and the "in an hour" bug.
- **Lock:** gate tests: no `from "frappe-ui"` Button/Switch/Badge in views or components; no `dayjs(` on a server datetime field.

### W4. Density rule (the "drowned in information" fix)
Every row answers **what** and **its state** in at most 2 lines:
- **Line 1:** the thing, in plain words.
- **Line 2:** the one fact you need, for example "Hafiz Salim · 6:31 pm" or "21 Sep".
- **Right side:** a status tag.

The same rule strips noise from every row:
- **Never shown:** raw document IDs (HR-LAP-…, 1387, HR-ISS-…), "by \<your own name\>", the full datetime with seconds, doctype names.
- **Lists:** show 5, then "See all". Inside "See all", load 20 at a time with "Show more (N left)", the same way Requests already does.
- **Endless scroll** (ListView) is removed.

Why: E5, E6, E10, and the owner's own "summary first, tap to narrow" rule.

---

## 3. What changes — screen by screen

### Home  (keep; 2 fixes)
- **Keep** the order: Today → News → Your week → Needs you. It was approved on 23 Sep.
- **Fix:** "Nothing booked. Next public holiday: Deepavali · Mon 9 Nov" wraps to 2 lines. Change it to line 1 "Next: Deepavali" and line 2 "Mon 9 Nov · public holiday". That keeps 2 short lines instead of one long sentence (E10).
- **Fix:** "3 days worked" and "Nothing to claim this week." read as two unrelated facts. Change them to line 1 "3 days worked this week" and line 2 "No overtime to claim".

### Calendar  (bug fix + finish the approved C-rulings)
- **Bug:** today, and any day with IN then OUT but no Attendance row yet, is drawn as **Worked** (the same paired-punch rule Home uses, shared as one helper). While you are still checked in, today shows "In progress". (E9, C10)
- **Bug:** the orange "Fix" dot never lands on today or on a shift that has not ended.
- **Legend:** add "Fix" (the orange dot) and "Overtime" (the lime dot). These are the only two dot kinds (ruling C4). Today's ring needs no key (C10).
- **Replace** the two underlined text links "All check-ins" and "Your shifts" with one list panel of two rows ("Check-ins ›", "Shifts ›"). Underlined links read as a web page, not an app.
- **Day sheet:** a past day with punches but no attendance gets the **Fix this day** button. Today it says "Nothing to do." (C5)

### Requests  (bug fix)
- **Bug:** "Needs attention" stops counting today, and the server returns the **dates** as well as the count.
- **Row:** "Tue 16 Sep has no attendance". With more than one day: "2 days have no attendance · 16, 18 Sep". Tap opens that day's sheet on Calendar, with the Fix button.
- **Keep** everything else. It was approved on 23 Sep.

### Score  (small)
- **Keep** the empty state. It is correct: it names who scores you, from the fenced payload (KR3).
- **Remove** the lime left bar on the empty card. An accent stripe signals something to act on, and there is nothing to act on here. Use a plain panel with an icon.

### More  (keep)
- No change beyond W1–W3. "Apps" stays.

### Help  (redesign — was the worst "drowning")
Today's stack is: segmented tabs, "Who to ask", a big lime button, 4 chips, then 29 rows of 3 lines each running under the tab bar.

Proposed stack:
1. The segmented control "HR" / "IT", without the "(29)" count. The count moves into the list heading.
2. **Open**: only the open and awaiting-you tickets, 5 shown, then "See all". Row line 1 is the title. Line 2 is the date, plus "Waiting on you" when that is true. The status tag sits on the right.
3. **Closed (N) ›**: one row that opens the full list in a sheet, 20 at a time.
4. **Who to ask ›**: one row at the bottom (see HR Contacts).
5. **New ticket**: the single primary button, placed under the list (E14; AC1 reachability, bottom third).

**Delete:**
- the 4 chips (grouping replaces them)
- the ID, "by \<you\>" and the type on every row
- the "details" preview on HR issue rows (it showed "Test")

**HR view (HR Issue Board):** HR keeps its board, but on `GListRow`. It shows 20 at a time instead of 500 at once.

Why: E5, E6, E8, E14, and owner feedback on the Help, HR Issues and IT Helpdesk screenshots.

### HR Contacts → "Who to ask" sheet
- **Change:** no separate page. "Who to ask" opens a sheet (medium detent). It shows **your manager** first, then the HR contacts. Each is one row with Call and Email buttons.
- **Empty state:** "HR hasn't listed contacts yet. Your manager: \<name\>." The old text, "Ask your administrator to assign the HR Manager or HR User role…", is wrong: the list also needs an **HR Contact** record per person (`hr_contacts.py:104-134`). It also tells staff to do an admin task.
- **Config note (not a code bug):** empty means no active HR Contact rows on the site. That is your Desk setup. This plan will not add them.
- **Why:** E7, E4. It also fixes the "old Frappe/old Nadi" look.

### Public holidays sheet
- **Change:** the title goes into the sheet's top bar, next to the Close X (E4). The extra `pt-6` and the second heading are removed, so no empty gap.
- **Change:** the holidays become a **flat grouped list on the sheet** instead of a glass card inside a glass sheet (E2). The next holiday is marked "Next".
- **Change:** the sheet opens at medium height and can be dragged up.

### Notifications  (redesign)
- **Header:** standard (W1), with "Mark all read" as the right-hand action. "9 Unread" as a huge number is removed. The unread count shows as a small line under the title instead.
- **Groups:** Today · Yesterday · Earlier. This is the industry pattern; see the weak spot in §1.
- **Row** (built from the notification's own reference fields, not the stored sentence):
  - Icon: the request kind (leave, overtime, claim, issue).
  - Line 1: **"Leave approved"**, "Overtime approved", "Issue completed", "Nurul asked for leave".
  - Line 2: "Hafiz Salim · 6:31 pm", in the right time zone.
  - Unread: a round dot plus a bold line 1. It replaces the 6px square.
- **Paging:** 20, then "Show more".
- **Why:** E5, E15, and the owner's "drowned with information".
- **Data:** stored messages are **not** rewritten (no data repair). The PWA stops rendering the raw sentence and builds the short line from `reference_document_type`, the status and the sender. The server also writes the short form for new notifications. **Check:** the push relay and Desk's bell text keep today's wording unless you say otherwise.

### Lists (Leave, Claims, Overtime, Shifts, Shift requests, Check-ins, Attendance requests)
- **Change:** they drop ListView's old header and endless scroll. Each becomes a W1 screen with the same chips and paging as "See all" on Requests. The rows use `GListRow`.

### Forms (Leave, Claim, Overtime, Shift, Attendance request, Issue, Ticket)
- **Change:** the W1 header. The primary button (Submit) sits at the bottom, above the safe area (AC1).
- **Change:** the confirm and toast wording stops showing doctype names (ruling L4, still open in code).
- **Change:** the date is pre-filled when a form opens from a Calendar day (C12).

### Profile, Change password, SOP detail, Ticket detail
- **Change:** the W1 header, and rows on `GListRow`. The frappe-ui Switch becomes `GSwitch`.

---

## 4. Out of scope (will not touch)
- Desk, doctypes, schema, patches (except the one-line boot time zone and the notification server text).
- KPI/Score fence (S1–S7): CSS and layout only, never a `v-if` that gates a section.
- Offline check-in (P3: never). Banked overtime (policy). Payroll.
- Historical data: stored notifications, attendance rows. Nothing is repaired.
- Adding HR Contact records on the site (your Desk config).

## 5. Build order (one deploy at the end)

| Slice | What | Main files | Lock (gate/test) |
|---|---|---|---|
| S1 | Time zone in boot; lists use `siteTime` | `hrms/www/hrms.py`, `utils/siteTime.js`, 6 item components | boot contract test; no-raw-dayjs gate |
| S2 | "Worked" is one rule: Calendar fill, Fix dot, Needs-attention dates | `hrms/api/calendar.py`, `requests_summary.py`, `home.py` (shared helper), `AttendanceCalendar.vue`, `daySheet.js`, `RequestBalances.vue` | today-not-flagged test; three readers agree (invariant) |
| S3 | Glass on chrome only; blobs out; scroll-edge fades | `glass-components.css`, `GPage.vue`, `App.vue`, `tokens.json` | backdrop-filter allow-list gate; contrast gate both themes |
| S4 | One shell: GAppHeader on every route | HRContacts, Notifications, Profile, ChangePassword, ListView, FormView, Sop*, Ticket* | every-route-has-BaseLayout gate |
| S5 | Notifications redesign | `Notifications.vue`, `pwa_notifications.py`, a `notificationLine.js` helper | row-shape test: no ID, no seconds |
| S6 | Help redesign + Who to ask sheet + HR board rows | HelpdeskHub, HelpdeskList, IssueList, HRIssueBoard, HRContacts→sheet | 5-then-See-all test; no-ID rows test |
| S7 | One row + one button sweep (9 rows, 10 buttons) | the listed components | no-frappe-ui-Button gate |
| S8 | Screen polish: Home lines, Calendar links + legend, Score card, Holiday sheet, Lists paging, Forms wording | as listed in §3 | surfaces gate; e2e walk of every route, light and dark, 360 / 390 / 430 |

**Every slice goes through these steps, in order:**
1. Write a failing test first.
2. Build the fix.
3. Run the design gates.
4. Run the e2e tests at phone widths.
5. Review.
6. Commit.

At the end there is one version bump, one tag, one push, and one deploy by you.

**Proof before "done":**
- A Playwright walk of **every route** as staff, approver and HR, in light and dark, with screenshots saved.
- No page errors.
- No row longer than 2 lines.
- No header that isn't GAppHeader.

## 6. Pipeline summary
Requirements (this file) → your go / sketch sign-off → slices S1–S8 (TDD, gates,
review per slice) → auto-commit → auto-review → version 2.0.0-alpha.5, tag, push
→ you deploy on Frappe Cloud. No manual steps for staff or HR. No patch is expected;
if S5's server text needs one, it self-runs.

## 7. Six-lens check (short)
1. **First principles:** a person opens Nadi to check in, see their day, ask for something, or find an answer. Every pixel that does not serve one of those costs attention.
2. **Assumptions challenged:**
   - "Glassmorphism = everything frosted" is wrong. Apple's own rule is glass on the controls only (E1).
   - "Today not green = attendance lost" is also wrong. The punches are safe; only the reading of them is late.
3. **Expert panel:**
   - An Apple designer would strip glass from the cards and keep it on the bars.
   - An accessibility reviewer would add that text on frost fails WCAG F83.
   - A PM would ask for day grouping on notifications; there is no guideline for it, only an industry norm.
4. **Simple explanation:**
   - Glass is the window frame, not the painting.
   - Every screen should wear the same frame.
   - Every row should say one thing.
5. **Critique:**
   - The biggest risk is S3: it touches every screen's look at once. The visual baselines get re-shot on purpose, and the contrast gate must pass in both themes.
   - S5 changes notification wording for Desk too, unless it stays PWA-only (the question below).
6. **Step by step:** the order runs from lowest to highest visual risk. The two correctness bugs come first so they ship even if you cut design scope.

## 8. Questions for you (only these)
1. **Sketch first?** I can show the 6 redesigned screens (Help, Notifications, Who to ask, Holiday sheet, Calendar, a list screen) as one page for sign-off before building, like Home/Requests. Recommended.
2. **Notification wording:** short wording in the PWA only (recommended, zero risk to Desk and email), or everywhere?

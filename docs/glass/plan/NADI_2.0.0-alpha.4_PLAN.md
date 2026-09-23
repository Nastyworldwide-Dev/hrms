# Nadi 2.0.0-alpha.4 — the plan

Status: **DRAFT for owner approval** (23 Sep 2026). No code until approved.
Follows: v2.0.0-alpha.3 (hotfix: sheets tappable, Reload works, refresh text hidden).
Basis: `docs/glass/audit/2026-09-23-basis.md` (every change cites a rule) plus the
owner's report on alpha.2 screenshots, 23 Sep.

## 0. The goal in one line

**Every page does one job, fits one screen where it can, and nothing is broken,
hidden wrong, or repeated.** Then an access matrix so "who sees what" is written
down, approved, and tested.

## 1. Rules this release follows (the bar)

| Rule | Source |
|---|---|
| Summary first, detail one tap away (progressive disclosure) | NN/g NG-PD (basis) |
| Compact: the page's main job fits the first screen at 390×844 | owner, 23 Sep; basis H8 |
| One primary action per screen | basis S-ONE |
| Plain words, sentence case, no block capitals | basis W-PLAIN, W-CASE |
| 44 px touch targets, visible focus, 4.5:1 text contrast | WCAG 2.2 AA 2.5.8, 2.4.7, 1.4.3 |
| No layout jump over 0.1 | Core Web Vitals CLS |
| Least privilege, need-to-know, deny by default | NIST AC-6, ISO 27001 A.5.15, OWASP A01 |
| A bug report is a symptom: fix the class, test the class | house rule (CLAUDE.md) |

**How we work (unchanged from alpha.2):** one cause per commit, red test first,
reviewed after each commit, live check on fresh.local at 390×844 in **dark and
light**, then one deploy at the end.

**New gate, because alpha.2 shipped a sheet nobody could tap:** a browser
test that opens **every** sheet and taps inside it, on phone and desktop,
runs before any push that touches a sheet, the dimming layer, or the page shell.

## 2. What's broken, and where it came from

| # | Symptom (owner, 23 Sep) | Cause | Status |
|---|---|---|---|
| H1 | Overlay over sheets, nothing tappable | dimming layer moved above sheets (25479308e) | **fixed in alpha.3** |
| H2 | "A new version is ready" → Reload does nothing | reload waited for an event that never came | **fixed in alpha.3** |
| H3 | "Refreshing…" over the page | pull strip visible at rest | **fixed in alpha.3** |
| B1 | Home "broken top to bottom" | **not yet diagnosed.** Screenshot shows status + Check out, then empty to the tab bar | P0 in this release |
| B2 | Calendar "entire calendar is like bug" | the sheet part was H1; rest to diagnose (below) | P0 |
| B3 | Day sheet says "No shift" on a worked day | `_my_day` reads Shift Assignment only; the shift is on the Attendance/Checkin | P0 |
| B4 | Calendar key shows only Worked / Leave / Rest day | key built from days present; Absent and Half day missing when none that month | check, P1 |
| B5 | Requests too long, needs scrolling | four big leave cards + two rows + button + tabs + chips | P0 redesign |
| B6 | Score mostly empty | no review → one card + a "Scored by" card, then nothing | P1 redesign |
| B7 | Other pages "same pass" | see §4 | P1 |

### Live audit, 23 Sep (fresh.local, 390×844, dark, every page)

Measured by a browser run; screenshots in `/tmp/audit-*.png`. Added to the plan:

| # | Defect | Where | P |
|---|---|---|---|
| A1 | **Help throws a JS error on every open** (`.catch` on undefined) | `HelpdeskHub.vue:149` | P0 |
| A2 | **Your details: 5 rows with blank labels** ("-" values) | `Profile.vue getFieldInfo` | P0 |
| A3 | **Money shows "INR"** (Help shows "RM") | Requests unpaid-claims row | P0 |
| A4 | **Stray colon in shift time** "9:00:–18:00" | Day sheet | P0 |
| A5 | **"Check in" shown on a day with no shift** (manager) | Home | P0 |
| A6 | **"Waiting 42" but only 4 rows**, no way to the rest | Requests | P0 |
| A7 | White camera box in the dark check-in sheet | Check-in sheet | P1 |
| A8 | Approval sheet shows system words ("Leave Application", "ID", "Open") | Approvals sheet | P1 |
| A9 | Notifications: every avatar "?", IDs break mid-word, raw system sentences | Notifications | P1 |
| A10 | Pages mostly empty: Home 65%, Score, More, Approvals ~60% | several | P1 (redesigns) |
| A11 | Team highlights "More" in the tab bar; scrolls 34 px for nothing | Team | P2 |
| A12 | Past days with no record look like future days; key covers "Rest day" only | Calendar | P1 (B4) |
| A13 | "1 leave request(s)" plural hack; an issue titled just "Issue" | Home, Help | P2 |
| A14 | Filter chips wrap to 2 lines; leave grid uneven 2+1 | Requests | P1 (redesign) |
| A15 | No tab bar on Notifications, Approvals, You | shell | P2 |

Not a defect: the test build showed "alpha.2" because it was built before the
version bump; Frappe Cloud builds from source on deploy.

## 3. Priorities

- **P0**: broken or blocks work. Must ship in alpha.4.
- **P1**: the page redesigns you asked for. Ships in alpha.4.
- **P2**: correctness and polish we already know about. Ships if time allows,
  otherwise alpha.5.
- **P3**: needs your ruling first. Only drafted here, no code.

## 4. Page by page

### Home — P0 (B1) then redesign
**First, diagnose (read-only):** open Home on the live site as you and as the
test personas, dark and light, and record what renders, what fails to load, and
what errors. Then fix the cause, not the look.
**Target layout (one screen, no scroll for the common case):**
1. Date title.
2. **Today card:** shift, time in, **Check in / Check out** (the one primary action).
3. **Waiting on you** (approvers only): counts that open Approvals.
4. **One announcement** (pinned or newest), "See all ›".
5. Nothing else. Personal request list stays on Requests.
**Done when:** fits 390×844 without scrolling for an employee with no approvals;
no empty band taller than one block; every block has a loading skeleton and an
error line; zero console errors.

### Calendar — P0 (B2, B3) then P1
- **B3 shift on the day sheet:** read the shift from the day's Attendance, then
  the check-ins, and only then the roster. Red test: a worked day with no
  Shift Assignment shows its shift.
- **B4 key:** always show the five kinds (Worked, Half day, Leave, Rest day,
  Absent) or only those present, as you prefer (ask). Today it silently drops some.
- **Day sheet:** one action, hours as time, team line (managers). Re-check with
  the new tap test.
- **Grid:** check every state in dark and light. Today's ring is readable on
  every colour. Future days are plain.
- **Links under the grid** ("All check-ins", "Your shifts"): keep, but as
  quiet rows, not bare underlined text.

### Requests — P1 full redesign (B5): compact, no scroll
**Job:** "ask for something, and see where my asks are."
**Target (one screen at 390×844):**
1. **New request**: the one primary button, at the top.
2. **Balances strip:** one compact row, e.g. "Annual 6 · Medical 13 · +3 ›".
   Tap opens all balances in a sheet. It replaces the four big cards.
3. **Needs attention:** one line each, only when non-zero ("1 day of overtime
   to claim ›", "1 day with no attendance ›").
4. **Your requests:** the last 5, each on one line ("Compassionate · 28 Aug ·
   Waiting"), "See all ›" opens the full list with filters.
5. Filter chips move into "See all", off the main page.
**Done when:** the page fits without scrolling for a typical employee (≤5
requests shown, ≤2 attention lines); no chip wraps to a second line.

### Approvals — P2
- Apply the new tap test to both sheets.
- An empty queue is one line, plus the answered links.
- Leave rows show the type, never the reason, to anyone but the approver.

### Team — P2
- Check the new "opens on the day" flow on the live site.
- Status words match the Calendar team line (done in alpha.2); keep a test.

### Score — P1 redesign (B6)
**Job:** "how am I doing, and who judges it?"
- **No review open:** one compact card, "No review yet. Hafiz scores you when
  HR opens one." Then last cycle's result if there is one. No second card
  repeating the name.
- **Review open:** the score ring, goals as short rows, "A figure looks wrong ›"
  (opens an HR issue, audit PAGE-15).
- Managers and CEO: team list stays, server-scoped (unchanged rule, protected).

### More — P2
- Keep: Help, SOPs, Announcements, Public holidays, Team, Apps.
- Rows compact. Apps only when the server offers them (done).

### You — P2
- Details sheet check on the live site; manager and shift lines.
- The segmented theme control: check dark mode contrast.

### Help — P2
- "Who to ask" row (done); empty states in one line.

### Notifications — P2
- Every tap lands on a real page (check-ins now land on Approvals).
- Mark as read works for staff (fixed 7 Sep; re-test).

### Announcements (Desk) — P2
- Put **HR Announcement** on the HR workspace so HR can find it without search.
- Test an image in an announcement on the live site (S3 storage).

## 5. Cross-cutting

| ID | Item | P |
|---|---|---|
| X1 | **Sheet tap gate:** browser test opens and taps inside every sheet, phone + desktop | P0 |
| X2 | Desktop: side menu dims under a sheet, **without** covering the sheet (APP-14, reopened by the hotfix) | P2 |
| X3 | Every page: skeleton while loading, one error line if it fails, never blank | P1 |
| X4 | Dark and light checked on every page before push | P1 |
| X5 | Refresh text: announce to screen readers on real pulls only | P2 |
| X6 | Update prompt: clear the fallback timer on success (review note) | P2 |
| X7 | Zero-balance skeleton collapse on Requests (review note) | P2 |
| X8 | Per-list "Team Requests" tabs (Shift list etc.) removed; Approvals owns them | P2 |
| X9 | Approvals scan: keyset paging instead of offset (ceiling marker) | P3, only if a missed row is reported |

## 6. Access matrix — P3 (drafted, needs your approval)

**Deliverable:** `docs/glass/ACCESS-MATRIX.md`, one page:
- Rows: every page and record kind (own request, team request, attendance,
  leave reason, pay, score, IC number, contact, announcements).
- Columns: Employee · Team lead/manager · Approver · HR · HR Manager · CEO ·
  System Manager.
- Each cell: **see / act / hidden fields**, and the rule that grants it
  (ownership, reports-to, routed, role).
**Checks before any change:**
1. Does Desk show a manager the **leave reason** of a direct report? (App never does.)
2. Which Employee fields can each person see on a colleague's record?
3. HR with no company assigned sees all companies ("open by default"). Keep or change?
**Then:** one automatic test per matrix line. **No access change ships without
your yes on that exact line.**

## 7. Order of work (slices)

1. Diagnose Home and Calendar live (read-only). Record the findings.
2. X1 sheet tap gate (test only).
3. P0 fixes: B1 Home cause, B3 shift, B2 remaining Calendar causes.
4. P1: Requests redesign → Score redesign → Home layout → X3/X4.
5. P2 list, in the order above.
6. Access matrix draft (docs only) for your review.
7. Full suite, gates, live check of every page in dark and light, CHANGELOG,
   version `2.0.0-alpha.4`, tag, push. One deploy.

## 8. Design work before code

Requests, Score and Home get a **sketch first** (like the alpha.2 tour page),
for your yes/no, before any code. Rule: owner signs off on layout changes
(house rule "mockup before UI code").

## 9. Needs your answer (only these)

1. **Calendar key:** always show all five kinds, or only the kinds in that month?
2. **Requests balances:** strip with the top 3 leave types, or only the two you use most (Annual, Medical)?
3. **Score with no review:** show last cycle's result, or nothing but the one line?
4. **Access matrix:** start drafting now (docs only), or after the pages?

## 10. Evidence still missing

- **Home on your phone:** what's broken. The page check running now will
  capture Home on the test site; your own account may differ (real data).
  Tell me what you see.

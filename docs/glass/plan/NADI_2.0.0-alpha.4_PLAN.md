# Nadi 2.0.0-alpha.4 — the plan

Detail, element by element: `NADI_2.0.0-alpha.4_DETAIL.md`.
Status: **APPROVED IN PRINCIPLE, owner rulings in (23 Sep 2026).** Code starts on
the owner's go. **One release, one deploy** at the end.
Follows: v2.0.0-alpha.3 (hotfix, deployed 23 Sep: sheets tappable, Reload works).
Basis: `docs/glass/audit/2026-09-23-basis.md` (every change cites a rule), the
owner's screenshots and report, and a live audit of every page (23 Sep).

## Goal

**Every page does one job, fits one screen where it can, and nothing is broken,
hidden wrong, or repeated.** Plus an approved access matrix.

## Owner rulings (23 Sep)

| # | Question | Ruling |
|---|---|---|
| R1 | Calendar key | **Always show every kind.** Add three new kinds: **Travel**, **Training**, and **Open request** (approvers and managers only: a day with a request waiting on them). |
| R2 | Requests balances | **Annual and Medical + "All balances ›".** The full list, when opened, is **compact too** (same rows), not big cards. |
| R3 | Score with no review | One line, plus the last result when there is one. **No repetition** (no second card with the same name). |
| R4 | Access matrix | **Draft now**, alongside the pages. Docs only; no access change without a yes per line. |

## How we work

- One cause per commit, **red test first**, review after each commit.
- Live check on fresh.local at **390×844, dark and light**, before the push.
- **Sheet gate (new):** a browser test opens every sheet and taps inside it,
  and closes it by the scrim and by Back, on phone and desktop. It runs
  before any push that touches a sheet, the scrim, or the page shell.
- **Seed data first:** the test user has no attendance, so worked days,
  leave, travel, training and absence are seeded on fresh.local (synthetic,
  named, removed after).
- One deploy: `2.0.0-alpha.4`, tagged.

---

## P0: broken, blocks work

| # | Problem | Where | Cause (found) or next step |
|---|---|---|---|
| P0-1 | **"Refreshing…" stays after you pull** (owner, after alpha.3) | every page with pull-to-refresh | Found: `GPullRefresh` waits for an `ionRefreshComplete` event that Ionic 7 does not send (Ionic docs: the refresher emits ionRefresh / ionPull / ionStart; the state ends when `complete()` is called), so our "Refreshing…" flag never resets. Fix: reset it when the pull finishes (ionPullEnd or our own completion). |
| P0-2 | **With a sheet open, taps go through to what's behind** (owner, after alpha.3) | every sheet | Found: the page is made inert, but the **tab bar and header sit outside the page**, so they stay tappable. Rule: a modal blocks everything behind it (Material 3 modal bottom sheet; WCAG 2.4.3 / WAI-ARIA dialog: content outside is inert). Fix: make the whole app shell behind the sheet inert and covered, sheet on top. |
| P0-3 | **Closing needs a pull-down; the motion is rough** (owner) | every sheet | Found: no Close button; tap-outside and Back are unreliable. Rules: NN/g bottom sheets — a visible **Close (X)** at the top, **Back closes**, **tap on the dim area closes**; Material 3 — tapping the scrim dismisses. Fix: add Close to every sheet, make both the others work, smooth motion in the app's timing. |
| P0-4 | Help throws an error on every open | `HelpdeskHub.vue:149` | `.catch` on an undefined value. |
| P0-5 | "Your details" shows 5 rows with no label | `Profile.vue` | Field labels are looked up in a list that lacks them. |
| P0-6 | Money shows "INR" (should be "RM") | Requests, unpaid claims row | Currency read from the wrong place. |
| P0-7 | Shift time shows a stray colon "9:00:–18:00" | day sheet | time trimmed wrongly. |
| P0-8 | Day sheet says "No shift" on a worked day | `calendar._my_day` | Reads the roster only. Read the day's attendance, then its check-ins, then the roster. |
| P0-9 | "Check in" shown on a day with no shift | Home | Show the button only when a check-in is possible. |
| P0-10 | "Waiting 42" but only 4 rows | Requests | The group has no "see all". Fixed by the Requests redesign (P1-2). |
| P0-11 | Home "broken top to bottom" | Home | Measured: 65% empty below one button. Fixed by the Home redesign (P1-1). |

## P1: the redesigns (sketch first → owner yes → code)

### P1-1 Home: one screen, never empty
**Rule:** a screen that shows nothing reads as broken (NN/g, empty states:
"explain, suggest, guide"; Carbon: say why there is no data and what to do).
So every Home block **always** renders, and says something useful when there is
nothing to act on. Nothing disappears.

1. **Date title.**
2. **Today** (always): shift and hours, and **Check in / Check out** when a
   check-in is possible. No shift today → "No shift today. Enjoy your day off."
3. **This week** (always): "4 days worked · 1h 30m overtime to claim ›", or
   "Nothing to claim this week."
4. **Coming up** (always): next leave, travel, training or public holiday, or
   "Nothing booked. Next public holiday: Deepavali · Tue 20 Oct."
5. **Waiting on you** (approvers and managers, always for them): counts, or
   "Nothing waiting on you."
6. **Latest announcement** (always): the pinned or newest one, or "No news."

Done when: fits 390×844 without scrolling; **no block ever disappears**;
no empty band taller than one row; each block has a skeleton and an error line.

### P1-2 Requests: compact, no scroll
1. **New request** on top.
2. **Balances line:** `Annual 6 · Medical 13 · All balances ›`. The full list
   opens in a sheet as the same compact rows (R2).
3. **Needs attention:** one line each, only when non-zero.
4. **Your last 5 requests**, one line each, and **See all ›**. Filters live in See all.
5. Approvers: "Answered by you" stays reachable from Approvals.
Done when: fits one screen for a typical employee; no chip wraps.

### P1-3 Calendar: every kind, readable
- **Key always shows all kinds (R1):** Worked · Half day · Leave · Travel ·
  Training · Rest day · Absent, and **Open request** for approvers and managers.
- **New day kinds from the server:** Travel (approved Travel Request dates, or
  an On Duty attendance request with a travel reason), Training (Training Event
  dates the employee attends), Open request (a request waiting on the caller
  that covers the day). Each is a new colour or outline, contrast-checked in
  both themes.
- Past days with no record look different from future days.
- Links under the grid become quiet rows.
- Day sheet: one action, hours as time, the team line for managers.
**Needs a source check first:** which of Travel Request / Training Event this
site actually uses. If a kind has no data source, it shows in the key only when
there is a source (reported back before coding).

### P1-4 Score: no empty tab
- No review: one line ("No review yet. Hafiz scores you when HR opens one."),
  plus "Last review: Q2 2026 · 82% ›" when there is one. The "Scored by" card
  is dropped (it repeated the name) (R3).
- Review open: the score, goals as short rows, "A figure looks wrong ›".
- Visibility rules unchanged (protected).

### P1-5 Sheets look and read right
- Approval sheet: plain words ("Time off", "Waiting"), not "Leave Application",
  "ID", "Open"; the reason reads left-aligned.
- Check-in sheet: no white camera box in dark mode.
- Every sheet: the same width and padding.

### P1-6 Notifications
- A real picture or initial instead of "?".
- Plain sentences ("Your leave on 22 Sep wasn't approved. See why ›"), no
  record numbers breaking mid-word.
- "Load more" styled like every other button.

### P1-8 Header: the Nadi mark, date inside the page (owner, 23 Sep)
- The Nadi mark (lime square with "n", already used in the side menu and as
  the app icon) at the left of every tab page's header. One shared component.
- The date leaves the header and becomes the first line of Home's Today card.
- Detail: `NADI_2.0.0-alpha.4_DETAIL.md` §1.3.

### P1-7 Every page: never blank, both themes
- Skeleton while loading, one error line if it fails.
- Checked in dark and light before push.

## P2: smaller known issues

| # | Item |
|---|---|
| P2-1 | Desktop: side menu dims under a sheet (APP-14, done safely with P0-2) |
| P2-2 | Team: tab bar highlights "More"; page scrolls 34 px for nothing; raw group code "NW0A" |
| P2-3 | "1 leave request(s)" → proper plural; an issue titled just "Issue" |
| P2-4 | No tab bar on Notifications, Approvals, You (decide: back button only, or tab bar) |
| P2-5 | The last per-list "Team Requests" tabs removed (Approvals owns them) |
| P2-6 | HR Announcement on the HR workspace in Desk; test an image on the live site (S3) |
| P2-7 | Update prompt: clear the fallback timer on success (review note) |
| P2-8 | Requests: no-balances skeleton collapse (review note) |
| P2-9 | More: rows compact; Apps only when offered (done) |

## P3: access matrix (docs now, changes need a yes per line)

Deliverable: `docs/glass/ACCESS-MATRIX.md`.
- Rows: every page and record kind (own request, team request, attendance,
  leave reason, pay, score, IC number, contact, announcements).
- Columns: Employee · Team lead/manager · Approver · HR User · HR Manager ·
  CEO · System Manager.
- Each cell: see / act / hidden fields, and the rule that grants it.
- Checks: does Desk show a manager the leave reason? Which colleague fields
  are visible? HR with no company assigned sees all companies: keep or change?
- One automatic test per approved line.

---

## Plan vs today vs research (23 Sep)

| Area | Nadi today (measured) | Research says | Plan item |
|---|---|---|---|
| Home | One block + button, 65% empty | Never leave a blank screen; explain and guide (NN/g empty states, Carbon) | P1-1: every block always renders |
| Sheets: blocking | Page inert, tab bar/header still live | Modal: everything behind is blocked (M3; WAI-ARIA dialog; WCAG 2.4.3) | P0-2 |
| Sheets: closing | No Close button; pull-down only | Close (X) + Back + tap on dim (NN/g; M3) | P0-3 |
| Sheets: use | Some flows live in sheets | Sheets for short tasks, not page-to-page flows; avoid stacking (NN/g) | P1-5: stacked sheets (confirm on sheet) reviewed |
| Pull to refresh | Text stuck after a pull | Refresher ends on `complete()` (Ionic) | P0-1 |
| Requests | Scrolls 426 px; chips wrap | Summary first, detail one tap away (NN/g progressive disclosure) | P1-2 |
| Score | One sentence on a whole tab | Same empty-state rule | P1-4 |
| Calendar key | Only kinds present | Consistent legend; don't encode by colour alone (WCAG 1.4.1) | P1-3: every kind, with a text label |
| Words | "INR", "Leave Application", "(s)" | Plain words (basis W-PLAIN) | P0-6, P1-5, P2-3 |
| Access | Rules in code, none written | Least privilege, need-to-know, deny by default (NIST, ISO, OWASP) | P3 |

## Order of work (one release)

1. **Seed data + sheet gate** (tests only).
2. **P0-1 to P0-9** (one commit per cause).
3. **Access matrix draft** (docs), in parallel.
4. **Sketches** for Home, Requests, Calendar key, Score → owner yes.
5. **P1-1 to P1-7** after the yes.
6. **P2** list.
7. Full suite, gates, sheet gate, live check of every page in both themes,
   CHANGELOG, version `2.0.0-alpha.4`, tag, push. **One deploy.**

## Sources

- NN/g: empty states (nngroup.com/videos/empty-states-in-application-design-guidelines),
  bottom sheets (nngroup.com/articles/bottom-sheet); Carbon empty states;
  Material 3 bottom sheets (m3.material.io/components/bottom-sheets/guidelines);
  Apple HIG sheets; W3C WCAG 2.4.3 focus order and H102 modal dialogs;
  Ionic ion-refresher docs.
- NN/g progressive disclosure; WCAG 2.2 AA (2.5.8 target size, 2.4.7 focus,
  1.4.3 / 1.4.11 contrast); Core Web Vitals CLS.
- NIST SP 800-53 AC-6, AC-5; NIST RBAC; NIST SP 800-162 (relationship rules);
  ISO/IEC 27001:2022 A.5.15; OWASP Top 10 A01; Malaysia PDPA 2010.

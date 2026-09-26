# Nadi 2.0.0-alpha.12: top-tier UI/UX pass (26 Sep 2026)

**Goal.** Every page, sheet, button and field meets one sourced rulebook, Apple first, phone first, then desktop. Every loading, empty, error and offline state is designed. Each rule is locked by a check, so it stays fixed.

- **Rulebook:** `docs/glass/audit/2026-09-26-a12/rules.md`. ~150 rules, each with a verbatim Apple quote (27 HIG pages fetched 26 Sep 2026, quotes machine-checked), or a named fallback (WCAG 2.2 SC, web.dev Core Web Vitals, NN/g).
- **Measurements:** `docs/glass/audit/2026-09-26-a12/*.json`, produced by two new scripts:
  - `frontend/e2e/page-audit.mjs`: alignment, type, weights, line height, contrast, targets, overflow. Runs at 402 and 1280, light and dark.
  - `frontend/e2e/states-audit.mjs`: forced slow, forced server error and forced offline, on all 36 screens.

---

## 1. What was measured (evidence, 26 Sep 2026)

### Critical: people see wrong or nothing

| # | Finding | Evidence | Rule |
|---|---|---|---|
| C1 | **The app has never worked offline.** The service worker is registered at `/assets/hrms/frontend/sw.js`, so it can only control that folder, never `/hrms`. An offline relaunch fails. | `navigator.serviceWorker.controller === false` on /hrms/home; offline reload: "WebKit encountered an internal error". `main.js:101` | O6, loading: "Show something as soon as possible" |
| C2 | **A failed load says "No requests yet".** When the server errors, 11 list and profile screens show their empty state instead of an error, so people think their records are gone. | states-audit: `error` has no alert on /attendance-requests, /leave-applications, /expense-claims, /shift-requests, /shift-assignments, /employee-checkins, /ot-requests, /more, /profile, /settings, /change-password | O1, R7 "never a loading state shown as nothing" |
| C3 | **Blank white screen while loading, on all 36 screens.** Nothing draws until the whole app has booted (`app.mount` waits for translations). | states-audit: `slow` screenshot is fully white at 700 ms on every screen | D1, loading: "they can interpret the lack of content as a problem" |
| C4 | **First open on a slow phone takes about 10 s to show anything.** 1.47 MB of JS before first paint; a PDF viewer (377 KB) and pdf.worker (1.3 MB) sit in the build. | Chromium with 4× CPU, 150 ms RTT, 1.6 Mbps: FCP = LCP = 10.4 s on /home, 73 requests | F1 (LCP ≤ 2.5 s, web.dev) |
| C5 | **The error message covers the page title.** The "Something didn't load" toast sits on top of the large title and bar buttons. | error screenshots of /more and /profile | G13, L3 |

### Alignment and layout

| # | Finding | Where | Rule |
|---|---|---|---|
| A1 | Desktop: inline titles are centred on the window, not the content: 172 pt off on 17 screens, 291 on Expenses, 340 on Change password. | page-audit 1280 | A4 |
| A2 | Desktop: the large title sits 184–200 pt left of the content column (Today, Requests, Calendar, Score, More). | page-audit 1280 | A3, layout: "Align elements to make them easier to scan" |
| A3 | Desktop: 5 different column widths (664 / 688 / 712 / 426 + side column / 352). | 1280 run | L9, A1 |
| A4 | Tablet 820: content is a 416 strip; the tab bar is 780 wide. | 820 run | L9 |
| A5 | "See all" in the announcements row floats mid-row (a flexed box 217 wide), not on the trailing edge. | /home, all sizes | A6 |
| A6 | Expense stats "RM 0 Pending / Approved / Rejected" are cut off: three boxes, each labelled twice. | /dashboard/expense-claims | T10, R8 |
| A7 | Two logos on desktop (sidebar and page); side-nav labels are 11 pt bold (the tab-label size, not 15/17). | /home 1280 | T1, N5 |

### Type and contrast

| # | Finding | Rule |
|---|---|---|
| T1 | Line heights are not iOS pairs: 17/20 (buttons, 18 screens), 12/18, 15/23, 34/34, 22/22, 16/24. Tokens `--g-type-button-label-line-height:1.2`, `caption 1.45`, `eyebrow 1.3`, `field-label 1.3`, `card-title 1.4`, `badge 1.2`. | T1 (typography table) |
| T2 | Weekday labels on the calendar grids: contrast 3.26 (light) and 3.52 (dark). Needs 4.5. | G9 (accessibility: "Up to 17 pts … 4.5:1") |
| T3 | Weight 420 ("Show more" on Notifications): not a system weight. | T2 |
| T4 | Tracking: Apple says −0.43 at 17 pt; the button token gives −0.17. | T5 |

### Spacing (31 values off the 4-pt scale, `/tmp/a12/tokens.md`)
`gap: 12px` is hard-coded in 20+ places, bypassing `--g-stack-*`. The row padding token `--g-pad-row` isn't used by `.g-form-row`. Stray values: 5, 7, 9, 14 and 29 px (tab label margin 5, auth subtitle 7, button trailing 9, empty action 14, row well 29×29), and empty-state side padding 24 where the gutter is 16.

### Keyboard
- Number fields use `type="number"` with no `inputmode`. iOS then shows the full keyboard, and the field can't hold "RM 12.50". There are no `inputmode` attributes anywhere. (virtual-keyboards: "Use the keyboard layout guide…"; rule K21)
- Nothing keeps the focused field or the Send bar above the keyboard (no `visualViewport` / `interactive-widget`). K23
- Return doesn't move to the next field. K24

### Words and redundancy (screenshots, all 36 screens)
- "Your day fixes", "Your time off", "Your expenses": W2 says to use "your" sparingly. Every list title starts with "Your".
- The "Who" row on your own request always shows your own name. "Company" is shown to single-company staff.
- "Reason: On Duty" then "Note: screen journey": two reason rows.
- Profile and Settings are the same page under two routes.
- Empty-state wording varies: "Nothing here yet", "No … yet", "Nothing open".
- "Leave left: None allocated yet" (Requests) versus "No leave allocated yet … People & Culture are setting this up" (Time off): one fact, two sentences.
- Notifications: 70 identical "W0 employee asked for time off" rows. No grouping by person or type (R6).
- Detail header status "Approved, not …" is cut off.

### Sorting
Lists default to `modified desc`. A request edited later jumps to the top, so it isn't in the order it was asked. Q1: requests order by creation; check-ins by time (already); notifications newest first (already).

### Apple conflict needing an owner ruling
- **Appearance picker** (Profile: Light / Dark / Automatic). Apple says: "Avoid offering an app-specific appearance setting." (dark-mode). Recommendation: remove it and follow the phone.
- **B1**: Apple allows "one or two" prominent buttons per view. The current rule (one) stays as the Nadi choice.

---

## 2. Per-page review

Format: purpose → today → fix → missing. States apply to every page (section 3).

### Tab roots
- **Today (Home).** Purpose: check in or out, and see what needs me.
  - Today: aligned on phone; "See all" floats; no skeleton; desktop title off the column.
  - Fix: A5, A2, C3.
  - Missing: the live shift ring (owner idea R1); pull-to-refresh already exists.
- **Calendar.** Purpose: see what happened on a day, and fix it.
  - Today: weekday contrast 3.26.
  - Fix: T2.
  - Missing: a month summary line ("18 days worked · 2 to fix") above the grid.
- **Requests.** Purpose: ask for something and follow it.
  - Today: "Leave left: None allocated yet" row, then "Your last 5" with an empty state.
  - Fix: one empty sentence per section; order by creation.
  - Missing: a status filter on "See all" (it exists; check it).
- **Score.** Purpose: see my review.
  - Today: one card with a brand-coloured left bar (the tint used as decoration, G6).
  - Fix: remove the bar and use a grouped row.
- **More.** Purpose: reach everything else.
  - Today: fine on phone; the desktop title is off.
  - Fix: A2.

### Lists (Fix a day, Time off, Expenses, Shift changes, Shifts, Check-ins, Overtime)
- Purpose: find a past request and see its status.
- Today: an empty state even when the server failed (C2); titles all "Your …"; order by modified.
- Fix: C2, the "Your" wording, Q1. Skeleton rows match the real row height.

### Forms (new Fix a day / Time off / Expense / Shift change / Overtime / Issue / Change password)
- Purpose: send one request correctly, first time.
- Today: good grouped form. The Send bar can sit under the keyboard; number fields get the wrong keyboard; the Overtime form shows a disabled Send with no reason next to it.
- Fix: K21 (inputmode), K23 (bar above the keyboard), K24 (Return = next), and a footer that says why Send is off.

### Details (a sent request)
- Purpose: see where my request is, and cancel it if needed.
- Today: "Who" = me, "Company", "Date" (a posting-date leak), status cut off in the bar.
- Fix: hide Who and Company on your own request; the status goes in a row (a status chip) instead of the cramped bar; "Date" → "Sent on".
- Missing: a timeline ("Sent 24 Sep → Approved 25 Sep by W0 approver").

### Other
- **Notifications.** Group 70 rows by day, then by person and type: "W0 employee asked for time off ×3". Five, then See all.
- **Help / Who to ask / Issue.** Good. "Report an issue" and "Who to ask" rows are repeated on /issues and /hr/issues (the same page twice).
- **You / Settings.** One page, one route. Appearance follows the phone (ruling).
- **Approvals.** Good. The summary is now a footer (alpha.11).

### Sheets (12, audited in alpha.11)
All pass the layout rules. Still to add: skeleton heights equal the final heights (sheet-shift audit already guards jumps).

---

## 3. States: one pattern everywhere

| State | Pattern | Rule and source |
|---|---|---|
| Launch | An instant shell painted from static HTML (brand ground, title bar, skeleton rows) before JS | loading: "Show something as soon as possible" |
| Loading | Skeleton rows the size of the real rows; no spinner in content; nothing for waits < 300 ms | NN/g skeleton screens; D2–D4 |
| Empty | One sentence: what is true, plus the action. Same shape on every screen | R7, W6 |
| Error | Inline in place of the content: what happened, plus **Try again** (44 pt), never "No … yet" | O1–O2, alerts: never just "Error" |
| Offline | The last data stays, with a quiet banner "No connection"; opening the installed app offline shows the last screen | O3–O6 |
| Slow (> 10 s) | The skeleton becomes "Still loading…" plus Try again | NN/g response times (10 s) |

---

## 4. Slices (one cause = one commit; red check first)

| # | Slice | Proves red with | Size |
|---|---|---|---|
| 0 | **Release tags.** GitHub Releases for v2.0.0-alpha.2…11 from the changelog; alpha.8/9 noted "shipped in alpha.10"; `scripts/release.sh` plus a test that every changelog version has a tag | `gh release list` | S |
| 1 | Gates: `page-audit` and `states-audit` join `design/gates/ios.mjs` at 402 and 1280 | today's counts (20 / 36 / 36) | S |
| 2 | **C2** error is not empty: ListView and the profile pages render ResourceError with Try again when the fetch fails | states-audit O1 = 11 | M |
| 3 | **C5** the error toast sits below the bar, inside the safe area | screenshot / box check | S |
| 4 | **C3** instant shell in index.html plus skeletons on every screen | states-audit D1 = 36 | M |
| 5 | **C1** service worker scope = /hrms (served from /hrms/sw.js or with a Service-Worker-Allowed header); app shell and last data cached | offline relaunch fails | M |
| 6 | **C4** performance: lazy-load the PDF viewer, split frappe-ui, preload the shell; target LCP ≤ 2.5 s on the throttled profile | 10.4 s | M |
| 7 | Type tokens: iOS line-height pairs, SF tracking, weight 420 → 400 | page-audit T9 = 18 | S |
| 8 | Contrast: calendar weekday labels ≥ 4.5 | G9 = 2 screens | S |
| 9 | Spacing: one scale, the stray values removed, `gap` from tokens | tokens audit list | M |
| 10 | Desktop and tablet shell: one column, title on its edge, inline title centred on the column, one logo, readable side nav | A3 = 6, A4 = 17 | M |
| 11 | Trailing accessories: "See all", row values | A6 | S |
| 12 | Keyboard: inputmode, Return = next, Send bar above the keyboard | new keyboard check | M |
| 13 | Words: "Your" titles, Who/Company on own requests, Date → Sent on, one empty-sentence shape, status chip in the detail | a copy test | M |
| 14 | Sorting: requests by creation desc | order check | S |
| 15 | Notifications grouped | row-count check | M |
| 16 | Redundancy: Profile = Settings (one route); /issues = /hr/issues for staff | route test | S |
| 17 | Lively Home: shift ring + check-in tick, mockup first (R1) | mockup | M |
| 18 | Expense stats: one grouped list, no cut-off text | T10 | S |

## Pipeline
Rulebook → gates go red → slices 0–18 in order, each red → green, one commit each → review hook → all gates green at 402/1280, light/dark, plus states → visual re-baseline → alpha.12 bump and changelog → tag + GitHub Release → push → the owner deploys.

## Rulings needed
- R1 Lively Home = shift ring + check-in tick? (recommended)
- R2 Desktop column 672 (Apple readable width, recommended) or 720?
- R3 Publish GitHub Releases (the repo is public)?
- R4 Remove the in-app Light/Dark picker and follow the phone (Apple)? (recommended)

---

## 5. Shipped in 2.0.0-alpha.12 (evidence)

| Slice | Commit | Before → after |
|---|---|---|
| 0 Release tags | b3951f68e | 0 → 8 GitHub Releases; `scripts/release.sh`; release-tags test |
| C2 Error is not empty | e136eca1f | 11 screens said "No … yet" on a forced 500 → "Could not load … Try again" |
| C5 Toast legibility | e638afc9d | title read through the banner → solid fill |
| C3 Launch shell | c46fab8a8 | blank white until boot → shell at 500 ms, light and dark |
| C1 Offline launch | 6a1f33315, 83956547e | no controller, offline reload failed → worker at /hrms, offline relaunch opens Today with the HTTP cache cleared (verifier REFUTED the first cut; fixed) |
| C4 Performance | 1bc9c3be9 | main JS 1.27 MB → 654 KB; FCP 10.4 s → 6.3 s (4× CPU, 150 ms, 1.6 Mbps) |
| T1–T3 + desktop | 0d9a0bd90 | page-audit phone 20 → 6, desktop 23 → 6; contrast 0; one 672 column |
| Keyboard | 66e04810b | no inputmode anywhere → decimal/numeric pads, Return=next, Send bar at the keyboard edge (538/538) |
| Trailing + gate | 77c7f2567 | See all mid-row → trailing; ios gate 4 → 7 audits, all 0 |
| Words + order | 5e2d036ef | Who/Company on own request, "Your …" titles, "Date", modified-desc order → fixed |
| R4 Theme | e29321971 | in-app picker → follows the phone |
| R1 Apple-way card | 2849a6c68, 71620e9f3 | state only → shift gauge (live: 4h 13m left, 53%), breathe, rolling time, drawn tick, forgot prompt, bell bounce |

## 6. Carried to the next release

- **Ionic core (542 KB)**: the next largest first-load cost; needs per-component imports.
- **Notifications grouping** (70 near-identical rows), **request timeline**, **Calendar month summary**.
- Six reviewed line-height findings (T9) kept as a baseline in the page-audit.

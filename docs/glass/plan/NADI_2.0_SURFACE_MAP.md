# Nadi 2.0 — surface map, grid and scroll budget

Companion to [NADI_2.0_UX_PLAN.md](NADI_2.0_UX_PLAN.md). 9 September 2026, branch
`nz-glass` at `adbae859c`. Every number here was measured, not estimated:

| Source | How | Rerun |
|---|---|---|
| Prototype, 36 screens + 5 sheets | Playwright, 390×844, every screen shown in the approver view. The prototype HTML is a design deliverable kept untracked at `<repo>/Nadi PWA UI UX 2.0/`; the measured JSON is committed, so the numbers here do not depend on rerunning it | `cd frontend && node e2e/prototype-measure.mjs > ../docs/glass/audit/2026-09-09-prototype-measure.json` |
| Shipped app, 36 routes | Playwright against `fresh.local:8080` (bundle rebuilt 9 Sep 03:02), signed in as the seeded audit employee, 390×844, light | `cd frontend && set -a && . ../.env && set +a && node e2e/app-measure.mjs > ../docs/glass/audit/2026-09-09-app-measure.json` |
| Block attribution | Same session, height of each child of the content column | inline script, see section 3 |
| Spacing census | Regex over 151 `.vue` files for Tailwind spacing, size, radius and text classes | inline script, see section 5 |

The prototype is the look we are going for. The gap between the two columns
in every table below is the work.

---

> **AMENDED 10 Sep 2026.** Q0 below is superseded by
> [NADI_2.0_AMENDMENT_A_LIQUID_GLASS.md](NADI_2.0_AMENDMENT_A_LIQUID_GLASS.md)
> §A1: the blob light field and blur-on-content retire (Q0a), Liquid Glass
> stays on the six chrome surfaces (Q0b). The "flat white / retire blur"
> verdicts in §1.3 apply to content surfaces only.

## 0. One decision this document needs first (Q0)

**The prototype is flat, light and still. The shipped app is Glass: light field,
specular bevels, blur, motion.** The Glass spec v1.1 and the phase 9 work order
(decisions D1–D3, 24 Aug) are the current build authority and they say Glass.
The compact proposal of 7 Sep already argued for "reduce decoration and motion,
keep Glass mainly in app chrome". The prototype goes further: no glass anywhere,
one page tint, white cards, one accent.

Recommendation: **the prototype's material becomes the spec.** Keep the token
*names* (the code already reads them), re-tune the *values* to the prototype,
retire the light field, bevel and blur layers. Record it as a spec addendum
(§18) before phase 0.6 below. This is a P&C and Nabil decision, not a design
one: it retires two months of Glass work on purpose.

---

## 1. The grid

The prototype is drawn on no explicit grid. Measured values sit on a mix of
4-point and odd numbers (13, 15, 18, 21, 23). We snap them to a **4-point grid
with an 8-point rhythm**: every spacing is a multiple of 4, every block gap a
multiple of 8, every tappable row a multiple of 4 and at least 44. The snap
never moves a value by more than 2 px, so the result looks like the prototype
and measures like a system.

### 1.1 Frame

| Part | Prototype (measured) | Grid | Token (name today → new value) | Shipped today |
|---|---|---|---|---|
| Reference viewport | 390 × 844 | same | `layout.viewport-*` | same |
| Screen gutter | 18 | **16** | `spacing.screen-gutter` 15 → 16 | `px-4` 16, `p-4` 16 |
| Content column | 390 − 2×18 = 354 | **358** | `layout.content-column` | 358 |
| Header (title row) | 21 px title, padding 12 18 8, sticky | height **56**, padding 12 16 8 | new `layout.header-height` 56 | ion-header **71** on every tab, plus a date eyebrow |
| Tab bar | 56 content + safe area (`--tab` 78 reserved) | **56** + `env(safe-area-inset-bottom)` | `layout.tabbar-height` 64 → 56, `tabbar-gap` 9 → 0 (bar sits on the edge) | 66 floating + 9 gap |
| Fold (usable height, tab-root screens) | 844 − 56 = 788 in a browser; 754 on a device with a 34 px safe area | budget **≤ 752** for a tab root | — | 844 − 66 − 9 = 769 |
| Sheet max height | 86 vh = 726 | **≤ 720** | `layout.sheet-max-height` | calc(100vh − 5rem) = 764 |
| Sheet radius | 22 | **24** | `radius.radius-tabbar` reused for sheets → `radius.sheet` 24 | 22 |

### 1.2 Spacing scale (the only values allowed)

| Step | px | Used for (prototype evidence) |
|---|---|---|
| s1 | 4 | pill padding-y (3 → 4), dot gaps, calendar cell gap (2 → 4) |
| s2 | 8 | chip gap (7 → 8), chip padding-y, sub-row gap, `.mt8` |
| s3 | 12 | control padding (13 → 12), row padding-y (13 → 12), `.mt12`, card padding-y (14 → 12) |
| s4 | 16 | gutter (18 → 16), card padding-x, row padding-x, `.mt16`, section-label top (15 → 16) |
| s5 | 24 | between a card and the next section label (15 + 9 ≈ 24) |
| s6 | 32 | done-screen top only |

Today the app uses **23 distinct gap classes, 18 distinct `py-` values and 39
arbitrary bracket values** (`gap-[13px]`, `mt-[0.5px]`, `h-[17px]`, …). The
scale above replaces all of them. `gap-8` (32 px) between Home's blocks is the
single biggest reason Home scrolls; it becomes 16 (s4).

### 1.3 Components, snapped

| Component | Prototype (measured) | Grid target | Existing component | Verdict |
|---|---|---|---|---|
| Card | pad 14 16, radius 16, white | pad **12 16**, radius **16** | `g-glass` panel, radius 20, blur | retune: flat white, radius 16 |
| List row (`.lrow`) | pad 13 16, 1 px divider, ≥ 50 h | pad **12 16**, min-h **56** | `GListRow` (7 uses) + 9 per-type `*Item.vue` | one `RequestRow`; retire the nine |
| Section label (`.sect`) | 12.5 px, pad 15 18 6 | 12 px, pad **16 16 8** | `g-eyebrow` 10.5 px uppercase tracked | retune: sentence case, 12 px, no tracking |
| Primary button (`.cta`) | pad 15, 16 px 700, radius 14, lime | h **52**, radius **16** | `GButton` primary, `pad-action` 17 18 = 54 h | retune |
| Ghost button | pad 13, 15 px 600, border | h **48**, radius 16 | `GButton` ghost | retune |
| Mini button (`.mini`) | h 34, 12.5 px, radius 20 | h **32**, radius 16 | none (header actions are icon-only) | new, header-right action |
| Chip | pad 7 13, 13 px, radius 20 | h **32**, pad 8 12 | `g-seg` (segmented, 50 h) | new `Chip`; `g-seg` stays for 2-way toggles at h 44 |
| Pill (status) | 11.5 px 700, pad 3 9, radius 20 | h **24**, pad 4 8 | `GBadge` (6 uses) radius 6 + inline labels in 6 files | one `StatusPill`, U4 vocabulary, radius 12 |
| Text control (`.control`) | pad 13, 15 px, min-h 50, radius 13 | min-h **48**, radius **12** | `GInput` radius 14 | retune |
| Segmented (`.seg`) | pad 3, buttons pad 10 | h **44** | `g-seg` 50 | retune |
| Field block (`.field`) | margin-top 14, label 12.5 + 6 gap | margin-top **16**, label 12, gap **8** | FormView field wrappers, 4 treatments | one `Field` |
| Summary block (`.summary`) | tint, pad 12 14, 13 px rows | pad **12 16** | none | new `RequestSummary` (plan slice 1.1) |
| Tile (`.tile`) | 2-col grid, gap 9, pad 11 13, min-h 56 | gap **8**, pad 12, min-h **56** | `g-cellgrid`, `GBalanceCard` | retune |
| Stats strip (`.stats`) | 4 cells, h 73, 19 px number, 10.5 px label | h **72** | `g-cellgrid--stat-4` 66 h | keep, retune |
| Calendar day (`.cal .d`) | 45 h, 13 px, 5 px dot | **44** h (touch minimum) | `g-cal` cells | retune; dot 6 |
| Approval card (`.appcard`) | pad 13 15, two 10 px-pad action buttons | pad **12 16**, buttons h **40** | `RemoteApprovals` cards | new `DecisionCard`, used by the unified queue |
| Timeline (`.tl .step`) | 17 px marker, pad 11 0 | marker **16**, row pad **12 0** | none | new `ProgressTimeline` (slice 1.3) |
| Sheet row (`.srow`) | h 50, pad 14 20 | h **52**, pad 12 20 | `GActionSheet` rows | retune |
| Type-grid button (`.tgrid button`) | 2-col, min-h 56, pad 10 12 | min-h **56**, pad 12 | none | new, the New-request sheet |
| Event card (`.ecard`) | 78 % width, pad 13 15, min-h 104 | pad 12 16, min-h **104**, snap-x | none | new (phase 3.6) |
| Tab bar button | 10 px 700 label, 21 px icon, 39 h | label 10, icon 24, h **48** | `BottomTabs` | retune |
| Toast | 13.5 px, pad 11 17, bottom = tab + 24 | pad 12 16, bottom = 56 + 24 | frappe-ui toast | keep, restyle |
| Empty state (`.empty`) | one line, 13.5 px, pad 26 20 | one line, pad **24 16** | `GEmptyState` (22 uses), icon + two lines + action | retune to one line (U2) |

### 1.4 Type scale (4-point line heights)

| Role | Prototype | Grid | Token today |
|---|---|---|---|
| Greeting / big number | 30 px 700 | **32 / 36** | `display-number` 31 |
| Greeting name | 23 px 700 | **24 / 28** | — |
| Screen title | 21 px 700 (18 on inner screens) | **22 / 28**, inner **18 / 24** | `screen-title` 21.5 |
| Stat number / `.num` | 19 px 700 | **20 / 24** | `stat-number` 22 |
| Sheet title | 16.5 px 700 | **16 / 20** | — |
| Button label | 16 px 700 | **16 / 20** | `button-label` 15.5 |
| Row title (`.ttl`) | 15 px 600 | **15 / 20** | `row-label` 12.5 (too small; the prototype's rows read at 15) |
| Control text | 15 px | **15 / 20** | 16 |
| Chip, body | 13 px 600 | **13 / 16** | `card-title` 12.5 |
| Sub, label, section | 12.5 px | **12 / 16** | `caption` 10.5 (too small) |
| Pill | 11.5 px 700 | **12 / 16** | `badge` 10 uppercase | the prototype's pills are sentence case |
| Tab label | 10 px 700 | **10 / 12** | `tab-label` 10 |

Weights: 700 for titles, numbers and pills; 600 for row titles and buttons;
400 for everything else. The prototype never uses 800; today's tokens do.
Family: the prototype uses the system stack; the spec pins Inter Tight (D1).
Keep Inter Tight for display roles only, system UI stack for body. Re-measure
row heights once after the family change.

---

## 2. Scroll budget

Rule: **a tab-root screen fits the fold in its resting state.** Forms and
detail screens may scroll, but their primary action is sticky and their first
field is above the fold. Lists show 10 rows then "Load more" (already the case)
under a sticky filter bar. Sheets never exceed 720.

Fold = 752 on a device (844 − 56 tab bar − 34 safe area − 2). The prototype
was measured in a browser with no safe area (fold 788); the shipped app's
detection found no tab bar, so its fold column is the raw viewport and its
overflow is understated by 75.

### 2.1 Tab roots and their prototype counterparts

| Screen | Shipped route | Shipped content (px) | Over fold (real, −75) | Prototype screen | Prototype content | Prototype over fold |
|---|---|---|---|---|---|---|
| Home | `/home` | **1382** | 613 | `s-home` | 723 | 0 |
| Calendar | `/dashboard/attendance` | **1362** | 593 | `s-attend` | 791 | 3 |
| Requests | `/dashboard/leaves` (+ `/dashboard/expense-claims` 773) | **1301** | 532 | `s-requests` | 637 | 0 |
| Score | `/dashboard/kpi` | 773 (empty state on the seed site) | 0 | `s-kpi` | **942** | 154 |
| More | `/more` | 773 | 0 | `s-more` | 707 | 0 |

Three of five shipped tab roots scroll by more than half a screen. The
prototype's five fit, except Score.

### 2.2 Everything else

| Screen | Shipped | Over | Prototype | Over | Note |
|---|---|---|---|---|---|
| Notifications | 1366 | 522 | `s-notifs` 508 | 0 | shipped shows 30 unread rows of 1120 px; prototype 5 rows + the quiet-clear line |
| Approvals | `/remote-approvals` 773 (empty) | 0 | `s-approvals` 761 | 0 | unified queue, 4 cards + geofence group |
| Leave list | `/leave-applications` **2589** | 1745 | `s-allreq` 615 | 0 | 80 seeded rows unpaginated in a `DIV.flex`; prototype 7 rows + 2 chip rows |
| Leave form | `/leave-applications/new` 844 (own scroller 681) | 0 | `s-leaveform` 606 | 0 | both fit; shipped Save bar at y 758 |
| Leave detail | `/leave-applications/:id` 1482 | 638 | `s-reqdetail` 653 | 0 | shipped renders the full form read-only; prototype: card + timeline + 3 actions |
| Attendance request detail | 1347 | 503 | `s-reqdetail` | 0 | same |
| Issue detail | 1158 | 314 | `s-issuedetail` 475 | 0 | same |
| Attendance request form | 989 | 145 | `s-genform` 484 | 0 | |
| Expense form | 844 | 0 | `s-expenseform` 814 | 0 | prototype nearly full; amount first |
| Travel form | — | — | `s-travelform` 915 | 71 | acceptable: form, sticky submit |
| Training form | — | — | `s-trainform` 912 | 68 | acceptable |
| Team | `/team` 773 (no reports on seed) | 0 | `s-team` **1144** | 356 | 11 people in 5 departments; collapse departments, 3 rows each then "N more" |
| Roster | `/team/roster` | — | `s-roster` **913** | 125 | table scrolls x; cover-by-day list is what overflows; move it above the grid |
| Balances | — | — | `s-balances` 780 | 0 | at the edge on device (754); drop the second CTA |
| Claims | — | — | `s-claims` 780 | 0 | same; trip block collapses when empty |
| Punch history | `/employee-checkins` 773 | 0 | `s-punches` 603 | 0 | |
| Sheets | — | — | New request 693, Day 322, Category 320, Reject 295, Withdraw 234 | 0 | all under 720 |

### 2.3 Where Home's 1382 px go (shipped, block by block)

| Block | Height | Share | Prototype equivalent |
|---|---|---|---|
| ion-header with date eyebrow | 71 | 5 % | header 56, date sits in the greeting |
| Greeting + Check In panel | 131 (+ gap 32) | 12 % | check-in card ~130 with state, shift and one CTA |
| Quick Links, 7 rows | **376** (+ gap 32) | 30 % | none; every link duplicated a tab or the New-request sheet |
| Requests panel, 10 rows | **674** | 49 % | "Needs you" 3 rows + "N more", 2 own requests |
| Column padding 24 / 32 and three 32 px gaps | 128 | 9 % | 16 px rhythm |

Removing Quick Links and capping the panels at three rows brings Home to
about 700 with the same data. That is the prototype's number.

### 2.4 Where Calendar's 1362 px go

| Block | Height | Prototype |
|---|---|---|
| Header + eyebrow | 71 | 56 |
| Calendar panel | 361 | 330 (cells 44 not 45, legend inside) |
| Stats strip | 66 | 72 |
| Four request sections with their own "Request X" buttons and empty states | ~800 | two rows: clock-in history, all requests; one "+ Request" in the header |

---

## 3. Surface map — every route and sheet

Verdicts: **keep** (retune only) · **merge** (folds into another surface) ·
**move** (same screen, new entry point) · **retire** (redirect kept) · **new**.
"Job" is the one thing the screen exists to do (U1). "Primary" is its one
primary action.

### 3.1 Shell

| # | Route / surface | Job | Primary | Prototype | Verdict |
|---|---|---|---|---|---|
| — | Tab bar | reach five roots | — | Home · Calendar · Requests · Score · More | keep, retune (Q1) |
| — | Header | title, back, one right action, bell + approvals badges on Home | — | `.hdr` | keep, drop the date eyebrow on every screen |
| 01 | `/login` | sign in | Sign in | — | keep |
| 02 | `/forgot-password` | recover | Send link | — | keep, add back control (C1) |
| 03 | `/change-password` | change | Save | — | keep |
| 04 | `/invalid-employee` | explain, route out | Contact HR | — | keep, add a way out |
| 05 | catch-all | say the page is missing | Go home | `s-stub` | keep |

### 3.2 Home and daily loop

| # | Route / surface | Job | Primary | Prototype | Verdict |
|---|---|---|---|---|---|
| 06 | `/home` | today + what needs you | Check in / out | `s-home` | keep; remove Quick Links; Requests panel → "Needs you" (3 + more) and "Your requests" (2) |
| — | `CheckInPanel` sheet | punch with location verdict | Confirm | check-in card flips in place | keep the sheet for GPS/selfie; the card shows state, shift, one CTA |
| — | `RemoteCheckinDialog`, `StrictRejectionDialog`, `LateCheckoutDialog` | explain the exception | Submit / Request correction | day sheet actions | keep; strict block gets "request a correction" (slice 1.7) |
| — | `PendingApprovalsBanner` | count pending | Open approvals | "Needs you" rows + header badge | merge into Needs you |
| — | `PushNotificationPrompt`, `InstallPrompt` | enable push / install | Enable | — | keep, once per install |
| 16 | `/notifications` | log of what happened | Mark all read | `s-notifs` | keep; rows become plain-language; quiet-clear count line; 10 + load more |

### 3.3 Calendar (today: Attendance)

| # | Route / surface | Job | Primary | Prototype | Verdict |
|---|---|---|---|---|---|
| 07 | `/dashboard/attendance` | the month at a glance | + Request (header) | `s-attend` | keep; four request sections → two rows; day sheet |
| — | Day sheet | act on one day | context action | `sheet-day` | new |
| 28 | `/employee-checkins` | raw punches by day | — | `s-punches` | keep, group by day, flag missing OUT, stats strip |
| 20 | `/attendance-requests` | list corrections | + New | `s-allreq` chip "Attendance" | merge into All requests |
| 21 | `/attendance-requests/new` | file a correction | Submit | `s-genform` (att) | keep, restyle, prefill from the day sheet |
| 22 | `/attendance-requests/:id` | see one | Withdraw | `s-reqdetail` | keep, becomes card + timeline |
| 23–25 | `/shift-requests[/new|/:id]` | shift change | Submit | `s-genform` (shift) | list merges; form and detail keep |
| 26–27 | `/shift-assignments[/:id]` | see my rostered shifts | — | calendar dots + team roster | merge: assignments render on the calendar; detail retires (164 px dead space today) |
| 29–31 | `/ot-requests[/new|/:id]` | overtime claim | Submit | `s-genform` (ot) | list merges into All requests (Money chip); form and detail keep |

### 3.4 Requests (today: Leaves + Expenses)

| # | Route / surface | Job | Primary | Prototype | Verdict |
|---|---|---|---|---|---|
| 08 | `/dashboard/leaves` | balances and recent leave | Apply | `s-requests` (hub) + `s-balances` | keep as the Requests hub; balance detail moves to `/balances` |
| 09 | `/dashboard/expense-claims` | money summary | Claim | `s-claims` | move: a card on the hub, full screen at `/claims` |
| — | New request sheet | choose a type with its balance | type | `sheet-new` | new; replaces Quick Links |
| 35 | `/leave-applications` | all leave | + New | `s-allreq` | merge: one All-requests list with type and status chips |
| 36 | `/leave-applications/new` | apply | Submit | `s-leaveform` | keep; type preset, per-type document, summary block |
| 37 | `/leave-applications/:id` | see one | Withdraw | `s-reqdetail` | keep; card + timeline; rejected is read-only |
| 38–40 | `/expense-claims[/new|/:id]` | claim | Submit | `s-expenseform`, claims list | list merges; form keeps: amount first, category sheet, receipt |
| 32 | `/replacement-leave` | bank and claims | Claim day | `s-balances` tile + `s-claim` | merge: tile on Balances, "Worked a rest day?" row |
| 33–34 | `/replacement-leave/claims[/new|/:id]` | claim a day | Send | `s-claim` | keep form; detail = reqdetail |
| — | Category sheet, Reject sheet, Withdraw sheet | one choice | — | `sheet-cat`, `sheet-rej`, `sheet-wd` | new (withdraw and reject exist as dialogs; restyle to sheets) |
| — | Done screen | confirm and route | Done | `s-done` | new (slice 1.2) |
| — | Holidays (component on Leaves) | plan around holidays | Bridge it | `s-holidays` | move to More → Holidays |

### 3.5 Approvals and team

| # | Route / surface | Job | Primary | Prototype | Verdict |
|---|---|---|---|---|---|
| 19 | `/remote-approvals` | decide check-ins | Approve | `s-approvals` + `s-geo` | merge: one Approvals screen (all six types + geofence group); geofence review keeps its own screen |
| — | `RequestActionSheet`, `WorkflowActionSheet` | decide on a document | Approve / Reject | `s-appdetail` + in-card buttons | merge into `DecisionCard` + detail with cover context |
| 13 | `/team` | who is in today | — | `s-team` | keep; group by department, collapse to 3 rows each; empty state when the caller manages nobody |
| — | `/team/roster` | week roster and cover | Assign | `s-roster` | keep; cover-by-day list first, grid scrolls x |

### 3.6 Score, SOPs, issues, long tail

| # | Route / surface | Job | Primary | Prototype | Verdict |
|---|---|---|---|---|---|
| 10 | `/dashboard/kpi` | scorecard | Report a figure | `s-kpi` | keep; KRA list caps at 4 then "all KRAs"; grade card first |
| 12 | `/sop` | find and read | Search | `s-sops` | keep; chips incl. "Needs reading" (phase 3.2) |
| 44 | `/sop/:id` | read and acknowledge | Mark as read | `s-sopdetail` | keep; adopt the shell |
| — | `SopFormSheet` (HR edit) | edit an SOP | Save | — | keep, HR only |
| 11 | `/issues`, 41–43 `/issues/new`, `/issues/:id`, `/hr/issues` | raise and follow | Report | `s-issues`, `s-issuedetail`, `s-genform` (issue) | Q3: Helpdesk becomes the surface; Employee Issue routes redirect |
| — | `/helpdesk`, `TicketNew`, `TicketDetail` | same | Send | same | keep, restyle |
| 14 | `/more` | reach the long tail | — | `s-more` | keep; History, Holidays, SOPs, Team roster, Settings, app links, log out |
| 15 | `/profile` | your record | — | `s-profile` | keep; scorecard and training rows |
| 17 | `/settings` | app settings | — | — | keep; one left edge; toggle off ≠ disabled |
| 18 | `/hr-contacts` | who to call | Call | — | keep; row on Profile |
| — | `ContactInfoSheet`, `ProfileInfoModal`, `FilePreviewModal`, `FileUploaderView` | detail / upload | — | drop zone in forms | keep; drop zone becomes the prototype's `.drop` |
| — | `ListFiltersActionSheet` | filter a list | Apply | chips | retire: chips replace the sheet |
| — | Flow map, role switch | prototype only | — | `s-flow`, "Viewing as" | not built |

New surfaces from phase 3 (travel, assets, training, events) are listed in the
plan's section 3.5; each arrives with its own row here when its decision lands.

---

## 4. Friction: taps and scrolls on the five journeys

Taps counted from the tab root; scroll is the overflow on the way.

| Journey | Shipped | Prototype | What changes |
|---|---|---|---|
| Check in | Home → Check In → sheet (GPS verdict) → Confirm = 3 taps, 0 scroll | card CTA → sheet → Confirm = 3 taps (the GPS step stays) | state and shift on the card; verdict says "free location" or the fence |
| Apply for annual leave | Home → Request Leave → pick type → dates → Save → lands on the raw form = 5 taps, 145 px scroll on the form, balance shown after the fact | Requests → + New → Annual (balance on the tile) → dates → Submit → Done = 5 taps, 0 scroll, balance-after and approver shown before Submit | summary block, done screen, no scroll |
| See a request's state | Home → scroll 674 px panel → row → full read-only form (1482 px) | Requests → All · 5 → row → card + timeline (653 px) | timeline replaces the form; withdraw is one sheet |
| Approve a leave | notification → detail → Review → sheet → Approve = 4 taps, or More → Remote Approvals (geofence only) | Home "Needs you" row → detail (balance, cover) → Approve = 2 taps; or Approve in the card = 1 | unified queue, context before the decision, pending state |
| Check this month's attendance | Attend tab → scroll 593 px past four request sections | Calendar tab, one screen, tap a day for actions | day sheet; two rows instead of four sections |
| Claim an expense | Expenses tab → View List → + New → form (multi-line table) | Requests → + New → Expense → amount, category sheet, receipt → Submit → Done | single line, receipt required, "paid with X payroll" |
| Read the notifications | 30 rows, 1366 px, doctype names in copy | 5 rows, plain copy, quiet-clear count | copy rewrite (slice 1.11), 10 + load more |

---

## 5. Redundancy census (why the UI work is bigger than it looks)

| Measure | Today | Target |
|---|---|---|
| `.vue` files | 151 | ~120 after the nine row components, four list routes and the filter sheet go |
| Distinct spacing / size / text classes | **265**, 39 of them arbitrary `[…]` values | the six-step scale + the type roles above; zero arbitrary values (gate) |
| Distinct `gap-*` | 23 | 3 (8, 12, 16) |
| Distinct `py-*` | 18 | 4 |
| Distinct `h-*` | 26 | component heights only |
| Distinct `text-*` | 39 | 12 type roles |
| Row-item components | 9 (`LeaveRequestItem`, `ExpenseClaimItem`, `OTRequestItem`, `ShiftRequestItem`, `AttendanceRequestItem`, `ShiftAssignmentItem`, `ReplacementLeaveClaimItem`, `EmployeeCheckinItem`, `ListItem`) + `GListRow` | one `RequestRow` (title, sub, pill, chevron) |
| Status labels declared inline | 13 labels across 6+ files (`Approved` ×6, `Pending` ×4, …) | one `StatusPill` map from the U4 vocabulary |
| Views that draw their own `h1`/`h2` instead of the shell | 9 | 0 |
| Field treatments in `FormView` | 4 (work order J3) | 1 `Field` |
| Busiest files by distinct spacing classes | `FormView.vue` 49, `HRIssueBoard.vue` 49, `RemoteApprovals.vue` 48, `SopDetail.vue` 46, `SopFormSheet.vue` 42 | each under 15 after adopting the kit |
| Empty states | `GEmptyState` in 22 files, icon + two lines + action | one line (U2), same component, new default |
| Error states | `ResourceError` in 29 files | keep |

The kit that replaces this is 22 primitives (section 1.3). Each existing
`G*` component maps to one of them: keep, retune or retire is in the table.

---

## 6. Gates that keep it true

Added to the plan's contract (U13, U14) and to phase 0.4:

| Gate | Check | Red today |
|---|---|---|
| U13 scroll budget | `app-measure.mjs` against the seeded site: every tab-root route's content ≤ 752 at 390×844; sheets ≤ 720; forms' first field above the fold | Home, Calendar, Requests, Notifications |
| U14 spacing census | the census script: no `[…]` spacing values; `gap-*` ∈ {2, 3, 4} (8/12/16); no `text-*` outside the type roles | 265 classes, 39 arbitrary |
| U15 one row, one pill | grep: no `*Item.vue` renders its own status label; every status string comes from `StatusPill` | 9 files |
| Coherence | the existing gate, plus "no date eyebrow outside Home" and "one h1 per screen from the shell" | 9 views |

Both measurement scripts are committed under `frontend/e2e/` and their JSON
under `docs/glass/audit/` so the numbers above can be re-shot after every
phase.

---

## 7. What this adds to the plan

| Plan item | Addition |
|---|---|
| Decisions | **Q0** the prototype's material becomes the spec (section 0) |
| Phase 0.2 | spec addendum §17 (contract) **and §18 (grid, type, components: sections 1.1–1.4)** |
| Phase 0.4 | gates U13–U15 |
| New 0.6 | token re-tune to the grid values, generated CSS regenerated, both themes re-measured |
| New 0.7 | the 22-primitive kit, built once, each with its measured height in a node test |
| Phase 1 | every slice adopts the kit as it touches a screen; no screen keeps bespoke spacing |
| Phase 2 | the surface-map verdicts are the scope: merge/move/retire rows are the redirects |

Nothing in this document changes application code. The prototype's numbers
are the target; the shipped numbers are the baseline; the grid is how the
build gets from one to the other without inventing a third set.

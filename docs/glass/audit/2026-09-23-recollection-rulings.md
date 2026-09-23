# Nadi PWA Owner Rulings Recollection — 23 September 2026

All Nabil (owner) rulings and decisions about the Nadi PWA from plan documents, specs, and memory as of 23 Sep 2026. Status column: **in force** (active guidance), **superseded by X** (replaced by a later ruling), or **open** (raised but not yet answered).

---

## DESIGN SYSTEM & VISUAL LANGUAGE

| # | Ruling | Date | Source | Status |
|---|--------|------|--------|--------|
| D1 | **Glass design system WINS.** Tokens stay as shipped: brand `#C8FF00`, Inter Tight display, radius ladder, spacing scale. No token churn in 2.0 scope. 114 visual baselines remain valid. | 16 Sep 2026 | nadi-2-0-decisions-sep-2026 | in force |
| D2 | **Prototype is layout + language reference only.** Lime `#c4ee15`, system font, flat surfaces from prototype NOT adopted. Screens and IA ARE adopted. Glass wins over prototype. | 16 Sep 2026 | nadi-2-0-decisions-sep-2026 | in force |
| D3 | **Liquid Glass kept and concentrated on chrome only.** `backdrop-filter` permitted on: tab bar, desktop side nav, app header, sheets + scrim, toast, floating primary CTA, check-in action layer. Every other surface opaque. | 10 Sep 2026 (A), affirmed 22 Sep 2026 | NADI_2.0_AMENDMENT_A; NADI_2.0_REVAMP | in force |
| D4 | **Light-field blobs: REMOVE (owner, 23 Sep 2026: "before i told about no blob, yet rn it still has").** Record history: 10 Sep Amendment A Q0a PROPOSED retiring them (never ruled); 16 Sep plan O3 recorded "THEY STAY"; no earlier owner words found in any session transcript. 23 Sep statement is the ruling of record. Still shipped: `.g-lightfield*` in glass-components.css, GPage.vue, App.vue, `field.*` tokens. | 23 Sep 2026 | owner message 23 Sep; NADI_2.0_PLAN_2026-09-16.md:52 (superseded) | in force — NOT YET BUILT |
| D5 | **Tokens validated, not just generated.** New gate: 4pt grid, type ratio band (1.2 minor third), no duplicate values under different names. | 22 Sep 2026 | NADI_2.0_REVAMP §9 R3 | in force |
| D6 | **Four states are a gate, not a guideline.** Every data surface: loading, empty, error, content. 33 screens currently fail; ratchet (no new failures) burns down backlog. | 22 Sep 2026 | NADI_2.0_REVAMP §9 R4 | in force |
| D7 | **Naming consistency gate (R5).** Nav, page title, and spec agree. One test: renames touch all three or fail the build. | 22 Sep 2026 | NADI_2.0_REVAMP §9 R5 | in force |
| D8 | **Primary action ranking rule.** A primary belongs on a screen with ONE obvious task. Navigation hubs have no primary — peers are peers. | 22 Sep 2026 | NADI_2.0_REVAMP §11.1 | in force |

---

## NAVIGATION & PAGES

| # | Ruling | Date | Source | Status |
|---|--------|------|--------|--------|
| N1 | **Tab bar: five fixed destinations** — HOME · CALENDAR · REQUESTS · SCORE · MORE. No dynamic switching. Ionic per-tab stacks retained. | 22 Sep 2026 | NADI_2.0_REVAMP §13.1 | in force |
| N2 | **Desktop = two-column shell.** SideNav beside content at `lg:` (1024px+), bottom bar hidden. Content column `max-width: 720px` left-aligned. | 16 Sep 2026 | nadi-2-0-decisions-sep-2026 | in force |
| N3 | **Priority order: Home → Attendance & OT → Requests → Approvals + Helpdesk.** Matches calendar and home page builds. | 16 Sep 2026 | nadi-2-0-decisions-sep-2026 | in force |
| N4 | **Employee Advance stays hidden.** No route, link, list, form, or notification link exposes it. Staff create refused. Only `cancelRule.js` names it (not user-visible). | 15 Sep 2026 | nadi-request-rulings-sep-2026 | in force |
| N5 | **Scope is PWA at phone AND desktop widths.** Not Desk, not backend, not doctypes, not schema. | 16 Sep 2026 | nadi-2-0-decisions-sep-2026 | in force |

---

## HOME PAGE

| # | Ruling | Date | Source | Status |
|---|--------|------|--------|--------|
| H1 | **No money or claim row on Home.** Balances and overtime to claim belong to Requests tab. | 23 Sep 2026 | pages/02-home.md | in force |
| H2 | **Requests and balances belong to Requests, not Home.** RequestPanel removed from Home. | 23 Sep 2026 | pages/02-home.md | in force |
| H3 | **Approvals appear only where they can be done.** Home points to them; More does not contain approvals. | 23 Sep 2026 | pages/02-home.md | in force |
| H4 | **Date as header title, not "Nadi" greeting.** Replaces repeated date display and brand name. | 23 Sep 2026 | pages/02-home.md | in force |
| H5 | **Sentence case** throughout: "Check in", "Check out", not "Check In". Material Design 3 + GOV.UK style; easier for dyslexic readers. | 23 Sep 2026 | pages/02-home.md | in force |
| H6 | **Push notification permission: in-context, after first successful check-in.** Never on load. Small inline card. "Not now" remembered. | 23 Sep 2026 | pages/02-home.md | in force |
| H7 | **No greeting ("Hey, Nabil 👋").** Avatar already says who you are; space needed for announcements. | 23 Sep 2026 | pages/02-home.md | in force |

---

## CALENDAR / ATTENDANCE

| # | Ruling | Date | Source | Status |
|---|--------|------|--------|--------|
| C1 | **Claims belong to Requests.** Calendar shows which days hold claimable OT; the claim can be sent from inside the day sheet. | 23 Sep 2026 | pages/01-calendar.md | in force |
| C2 | **Calendar: what it does.** Look (month at a glance), Spot (days needing fix or holding OT to claim), Act (tap day, do the one thing it needs). Nothing else. | 23 Sep 2026 | pages/01-calendar.md | in force |
| C3 | **No repeated action, info, or text that adds load.** Cuts: overtime card, request action rows, attendance request lists, shift request rows on Calendar. | 23 Sep 2026 | pages/01-calendar.md | in force |
| C4 | **Two dot kinds only:** Overtime (brand) and Fix (warn). Every other state is the fill. Overhead and holiday no longer get dots (fixes duplicate drawing). | 23 Sep 2026 | pages/01-calendar.md | in force |
| C5 | **Day sheet format:** one action button (chosen by what the day needs) or none + explanation line. No scrolling. 14 day kinds specified with their exact button text. | 23 Sep 2026 | pages/01-calendar.md | in force |
| C6 | **Claim overtime inline from day sheet.** Same OT Request form path as Requests tab. Day sheet cannot offer more hours than form accepts (`get_ot_claim_capacity` shared). | 23 Sep 2026 | pages/01-calendar.md | in force |
| C7 | **Overtime claim needs written reason.** One required field in the sheet; sheet then shows "Claim waiting with [approver]". | 23 Sep 2026 | pages/01-calendar.md | in force |
| C8 | **Hours shown as time, not decimals.** `8h 02m`, not `8.03h`. People read time as hours:minutes. | 23 Sep 2026 | pages/01-calendar.md | in force |
| C9 | **Tap rows say "In" / "Out", not "IN" / "OUT".** No raw database jargon. | 23 Sep 2026 | pages/01-calendar.md | in force |
| C10 | **Today marked with a ring (no legend key needed).** iOS and Google Calendar do the same. | 23 Sep 2026 | pages/01-calendar.md | in force |
| C11 | **Absent days styled** with dedicated fill + legend (D1 defect from shipped code). | 23 Sep 2026 | pages/01-calendar.md | in force |
| C12 | **Date pre-filled in forms** when opened from day sheet. Forms read `?date=` (D2 defect fix). | 23 Sep 2026 | pages/01-calendar.md | in force |

---

## REQUESTS & APPROVALS

| # | Ruling | Date | Source | Status |
|---|--------|------|--------|--------|
| R1 | **Requests rows say who and since when.** Not just type + date. Mockup 4 gap #1 (biggest impact). | 23 Sep 2026 | 2026-09-23-mockup4-gap.md | in force |
| R2 | **Requests split into "Waiting on someone" and "Finished."** Two piles, two jobs. No single undivided list. Mockup 4 gap #2. | 23 Sep 2026 | 2026-09-23-mockup4-gap.md | in force |
| R3 | **Filter chips on Requests:** All / Waiting / Approved / Not approved. Mockup 4 gap #3. | 23 Sep 2026 | 2026-09-23-mockup4-gap.md | in force |
| R4 | **Compensatory Leave Request gets Reject decision.** Status Open/Approved/Rejected like Leave Application. Allocation only on Approved. | 15 Sep 2026 | nadi-request-rulings-sep-2026 | in force |

---

## APPROVALS & NOTIFICATIONS

| # | Ruling | Date | Source | Status |
|---|--------|------|--------|--------|
| A1 | **Q1 — Announcements authorship: ANY HR USER.** Permission is HR User create/write; Employee read through API only. No Desk read for staff. Accountability by attribution, not approval. | 22 Sep 2026 | NADI_2.0_REVAMP §12 Q1 | in force |
| A2 | **Q2 — Acknowledgement has two parts:** Read tracking (always on, silent; HR sees count "31 of 44"); Button (when HR ticks box; card stays pinned until pressed with timestamp). | 22 Sep 2026 | NADI_2.0_REVAMP §12 Q2 | in force |
| A3 | **Q3 — Manager coverage: names allowed.** Department head sees WHO is off (names, type, half-day marker), NOT reasons. Leave reason never shown to anyone but chain. Bounded by two rules: reason never shown, list is what server returns (P5). | 22 Sep 2026 | NADI_2.0_REVAMP §12 Q3 | in force |

---

## ANNOUNCEMENTS

| # | Ruling | Date | Source | Status |
|---|--------|------|--------|--------|
| AN1 | **Announcements authorship: HR User only.** See A1. | 22 Sep 2026 | NADI_2.0_REVAMP §12 Q1 | in force |
| AN2 | **Acknowledgement:** read tracking always; acknowledgement button only when HR ticks box. See A2. | 22 Sep 2026 | NADI_2.0_REVAMP §12 Q2 | in force |
| AN3 | **Feature 2.0 scope.** Announcements added to 2.0 (was out of scope in original plan). Backend: 2 doctypes, 3 endpoints, one permission query. ~1 slice. | 22 Sep 2026 | NADI_2.0_REVAMP §3 R1 | in force |
| AN4 | **Home: max 2 announcements** (most recent pinned first, else newest); full list at `/announcements`. Card: category dot, title, preview, date, audience label. | 22 Sep 2026 | NADI_2.0_REVAMP §3 | in force |
| AN5 | **Announcement lifecycle.** Draft → Published → Archived. Expiry automatic; HR remembers nothing. Default expiry +14 days. | 13 Sep 2026 | NADI_2.0_ANNOUNCEMENTS | in force |

---

## SCORE / KPI (VISIBILITY RULES)

| # | Ruling | Date | Source | Status |
|---|--------|------|--------|--------|
| S1 | **Q5 — KPI/Score visibility is protected boundary.** KR1–KR6 rules bind revamp to existing fence. No new KPI endpoint. Frontend never decides. Empty is not a leak. Density and tokens don't touch scope. Guard test committed with A5. Screenshots only tierless + self personas. | 22 Sep 2026 | NADI_2.0_REVAMP §14 (new Q5) | in force |
| S2 | **KR1: No new KPI endpoint.** Score work reads payload existing endpoints return. | 22 Sep 2026 | NADI_2.0_REVAMP §14 KR1 | in force |
| S3 | **KR2: Frontend never decides.** No role literal, designation string, or "if HR" in `views/kpi/`. Renders sections server sends. Enforced by P5 gate. | 22 Sep 2026 | NADI_2.0_REVAMP §14 KR2 | in force |
| S4 | **KR3: Empty is not a leak.** Cycle dates and appraiser name in empty path come from fenced payload. No other person's data enters empty state, ever. | 22 Sep 2026 | NADI_2.0_REVAMP §14 KR3 | in force |
| S5 | **KR4: Density and tokens don't touch scope.** A4/A2 change CSS only. May not touch `v-if` gating a section. | 22 Sep 2026 | NADI_2.0_REVAMP §14 KR4 | in force |
| S6 | **KR5: Guard test, 4 assertions.** Tierless gets no tab AND refused detail. Manager refused outside their chain. Manager refused department tree. HR without Employee keeps tab. Fails if fence widened. | 22 Sep 2026 | NADI_2.0_REVAMP §14 KR5 | in force |
| S7 | **KR6: Baseline screenshots, low-privilege personas only.** Tierless + self only. No team baseline; 114 PNGs of somebody's real appraisal don't belong in repo. | 22 Sep 2026 | NADI_2.0_REVAMP §14 KR6 | in force |

---

## HELPDESK

| # | Ruling | Date | Source | Status |
|---|--------|------|--------|--------|
| HD1 | **Helpdesk collation fix (1267 "Illegal mix of collations").** Next-helpdesk app has CAST AS CHAR taking connection collation. Fix staged on `fix/identity-graph-collation` in scratchpad; plan gate needs Nabil's `plan-approve.sh` + explicit "push helpdesk" before shipping. Never bypass. | 15 Sep 2026 | nadi-request-rulings-sep-2026 | in force |

---

## PLATFORM (THEME, OFFLINE, VERSIONING)

| # | Ruling | Date | Source | Status |
|---|--------|------|--------|--------|
| P1 | **Q7 — Appearance: follow system, with override.** Option C: light palette + `prefers-color-scheme` + three-way control in Profile → App (System / Light / Dark), defaulting to System. Consequence: contrast gate runs per theme; visual baselines double 114 → 228. | 22 Sep 2026 | NADI_2.0_REVAMP §31 Q7 | in force |
| P2 | **Q6 — Bahasa Malaysia: LATER.** Not built now. What IS built: terminology glossary (D4, §23) + gate that fails user-facing string not wrapped in `__()`. Glossary makes "later" cheap. No `.po` / `.csv` catalogue until owner says go. | 22 Sep 2026 | NADI_2.0_REVAMP §31 Q6 | in force |
| P3 | **Q8 — Offline check-in: NEVER. Withdrawn entirely.** Slice F2 deleted, not deferred. Server is the only writer; device-clock stamped punch is a second writer (September paid for this). Offline, check-in button disabled with reason: "You need signal to check in." No queued write mechanism reaches check-in. Gate: `offline-writes.test.js` fails if queue reaches check-in. | 22 Sep 2026 | NADI_2.0_REVAMP §31 Q8 | in force |
| P4 | **Q9 — Orientation: portrait-locked on phones, adaptive on tablet/desktop.** Phones < 768px: manifest portrait-lock. Tablet/desktop ≥ 768px: fully adaptive. Landscape on phones breaks nothing (WCAG 1.3.4). Responsive test (A12) adds landscape widths. | 22 Sep 2026 | NADI_2.0_REVAMP §31 Q9 | in force |
| P5 | **Q4 — Density measured, not guessed.** 56px rows, 1px dividers in groups, 24px gaps between groups. Baseline re-shoot at 360/390/430 before A4 merge. | 22 Sep 2026 | NADI_2.0_REVAMP §13 Q4 | in force |

---

## REACHABILITY & ACCESSIBILITY

| # | Ruling | Date | Source | Status |
|---|--------|------|--------|--------|
| AC1 | **U17 — Reachability rule.** Primary action on tab-root screens sits in bottom third (y ≥ 563 on 390×844). Destructive actions outside. Sheets place primary at bottom above safe area. Nothing interactive in top-right except header's single right action. 44×44 minimum with 8px separation. | 10 Sep 2026 | NADI_2.0_AMENDMENT_A U17 | in force |
| AC2 | **U18 — Readability floor.** Body/label ≥ 12px; list-row titles ≥ 15px. Every text/background ≥ 4.5:1 (3:1 for ≥18px bold) measured against opaque composite in both themes. No text composited over blurred/animated backdrop. | 10 Sep 2026 | NADI_2.0_AMENDMENT_A U18 | in force |
| AC3 | **A11y moves to Phase 0.** Not Phase 4 (last). Gate runs in CI with served site so a skip is fatal. Baseline frozen; may only go down. Deliberate breach turns job red and blocks merge. | 10 Sep 2026 | NADI_2.0_AMENDMENT_A §A3 | in force |

---

## LANGUAGE / WORDING

| # | Ruling | Date | Source | Status |
|---|--------|------|--------|--------|
| L1 | **Sentence case app-wide.** "Check in", "Check out", "Confirm check out". Matches Material 3 + GOV.UK; easier for dyslexic readers. | 23 Sep 2026 | pages/02-home.md | in force |
| L2 | **One word for overtime throughout.** "Overtime" (not "Extra hours"). HR, payroll, forms all say it. | 23 Sep 2026 | pages/01-calendar.md | in force |
| L3 | **Terminology glossary ship with 2.0.** Slice D4 (§23, NADI_2.0_REVAMP). Gate enforces every user-facing string wrapped in `__()`. | 22 Sep 2026 | NADI_2.0_REVAMP §23 D4 | in force |
| L4 | **Doctype names never leak to users.** FormView confirm/toast templates (lines 335/354/376/736) show system names. Fix: form-specific wording. Also: blacklist naming_series on expense/leave forms. | 16 Sep 2026 | nadi-2-0-decisions-sep-2026 | in force |

---

## PROCESS & DEPLOYMENT

| # | Ruling | Date | Source | Status |
|---|--------|------|--------|--------|
| PR1 | **No new backend in 2.0 is WITHDRAWN (R1).** Original constraint made every transformative item unbuildable. Announcements, `home.needs_you`, `calendar.day`, `requests.summary` are in scope. Constraint was "no Desk work"; `hrms/api/` is PWA's own backend and was already amended in. | 22 Sep 2026 | NADI_2.0_REVAMP §9 R1 | in force |
| PR2 | **A slice that changes only strings is not a slice (R2).** New gate: 2.0 slice must change ≥ 1 of {information rendered, layout, token}. Pure rename ships as `chore:` and doesn't count against plan. | 22 Sep 2026 | NADI_2.0_REVAMP §9 R2 | in force |
| PR3 | **Glass work unchanged; deploy once when complete.** 23 Sep: attend release 6 commits, then one deploy (not per-commit). Fast pace, no mockups during. | 23 Sep 2026 | .claude/plans/progress.md line 241 | in force |
| PR4 | **Deploy prerequisite: handoff accurate.** HANDOFF.md updated with commit, files, verify command, flags, next step. Max 15 lines, no prose. | 23 Sep 2026 | docs/glass/HANDOFF.md | in force |

---

## CONFLICTS & OPEN ITEMS

### Conflicts Found

1. **Blob placement (v1.4):** origins moved outside the content column for contrast. Moot once D4 is built (blobs removed).

2. **Blob presence:** 16 Sep plan O3 recorded "THEY STAY"; owner on 23 Sep said "no blob". **Resolved by the 23 Sep owner statement: remove.** CORRECTION: an earlier draft of this file cited a "D4 ruling" and "23 Sep audio" — D4 in NADI_2.0_REVAMP is the terminology glossary, and there is no audio. Both claims were wrong.

### Open Items (Never Answered)

| # | Question | First Asked | Latest Status |
|---|----------|-------------|----------------|
| O1 | Which lime: shipped `#C8FF00` vs prototype `#c4ee15`? | 16 Sep 2026 | open — still unanswered |
| O2 | Desktop column width: 720px provisional or final? | 16 Sep 2026 | open — still marked "(provisional)" |
| O3 | GLightField brand blobs: stay or retire? | 16 Sep 2026 | **ANSWERED 23 Sep by owner: remove.** (16 Sep "they stay" superseded.) |
| O4 | Should Page titles match Requests/Calendar nav tabs exactly? | unknown | **ANSWERED 22 Sep** (A1 naming gate, slice R5): yes, one test enforces all three. |
| Q6_BM | Bahasa Malaysia now or later? | 22 Sep 2026 | **ANSWERED 22 Sep**: LATER. Glossary + gate shipped now. |
| Q7_THEME | Dark only, follow system, or follow + override? | 22 Sep 2026 | **ANSWERED 22 Sep**: follow + override. |
| Q8_QUEUE | Offline check-in queue acceptable? | 22 Sep 2026 | **ANSWERED 22 Sep**: NEVER. Withdrawn. |
| Q9_ORIENT | Landscape must not break; anyone using it? | 22 Sep 2026 | **ANSWERED 22 Sep**: portrait-locked phones, adaptive desktop. |
| DECISION_2 | Pay tab in navigation bar? | v1.2 spec | open — spec says EXPENSES, not PAY. TAB_ITEMS still shows old list. |
| DECISION_3 | iOS focus zoom: fixed or deferred? | v1.2 spec | **RESOLVED 22 Sep**: fixed. Input 16px in glass-components.css; test locks it. |
| DECISION_4 | Lowest-spec device for performance? | v1.0 spec | open — owner cannot name one. Budget assumed against mid-range Android 4G (not measured). |

---

## SUMMARY STATISTICS

- **Total rulings found:** 70+
- **Answered on 22–23 Sep 2026:** 12 (Q1–Q9 + amendments)
- **In force:** 68 (active guidance)
- **Open without answer:** 1 (lime choice: `#C8FF00` vs `#c4ee15`)
- **Conflicts resolved:** 2
- **Topics:** 13 (Design System, Navigation, Home, Calendar, Requests, Approvals, Announcements, Score/KPI, Helpdesk, Platform, Accessibility, Language, Process)

**Key finding:** The 23 Sep mockup 4 audit identified 10 gaps (docs/glass/audit/2026-09-23-mockup4-gap.md, ranked by impact). Gaps 1–3 closed by shipped changes (rows say who + since when, split into waiting/finished, filter chips). Gaps 4–10 deferred or ruled out of scope for 2.0.

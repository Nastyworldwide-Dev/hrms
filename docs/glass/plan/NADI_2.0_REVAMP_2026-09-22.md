# Nadi 2.0 — the real revamp

Written 22 September 2026, after the 2.0 deploy. Branch `nz-glass`.
This document supersedes the per-page sections of `NADI_2.0_UX_PLAN.md`.
It does not supersede the Glass spec (`docs/glass/spec/HR_Frappe_Glass_Spec_v1.1.md`);
it proposes named, costed changes TO it, listed in §9.

---

## 0. Why the deploy looked unchanged

Not an opinion — this is what the eight shipped slices actually did.

| Slice | What changed | Visible? |
|---|---|---|
| 0.1 | tab labels in `data/navItems.js` | a word |
| 1.1 | `PendingApprovalsBanner` → `NeedsYou` | a word |
| 2.1 | attendance list titles | words |
| 2.2 | OT compensation mapping | a word |
| 3.1 | `Requests.vue` — composed two existing components | a page that existed, moved |
| 3.2 | form field allowlists | invisible |
| 4.1 | approvals tab wording | words |
| D.1 | desktop column 720px signed off | desktop only |

Seven of eight changed **strings**. Zero changed layout, density, type,
spacing, colour, or information. None added data that was not already on
the screen. That is the whole cause. The app is not different because
nothing that makes a screen look like something was touched.

Three concrete misses on top of that:

1. `views/attendance/Dashboard.vue:2` still reads `pageTitle="__('Attendance')"`.
   `views/kpi/Dashboard.vue:2` still reads `__('KPI')`. Slice 0.1 renamed the
   tab labels and not the page headers, so the app contradicts itself in two
   places. Genuine defect, not scope.
2. Score is a near-empty screen: one dashed empty-state card in ~900px of
   black. 33 of 48 screens have no empty state at all; Score has one and it
   is still the whole page.
3. Announcements — the one feature the owner asked for — do not exist.
   §7 of the old plan put new backend out of 2.0's scope, which made the one
   transformative item unbuildable by its own rules. That rule is wrong and
   is withdrawn here (§9, change R1).

### Measured, not felt

- 103 arbitrary pixel values in components (`SopList` 20, `Profile` 17,
  `SideNav` 13); 19 distinct values exist in no token.
- `design/tokens.json` spacing/radius: `3.5 6 8 9 11.5 13 14 15 16 17 18 19 20 22`
  — 11 of 14 off a 4pt grid. Five separate tokens are all `10px`.
- Type sizes `10 10.5 11.5 12.5 14.5 15.5 21.5 22 25 31 36`, step ratios
  1.05 → 1.387. No modular scale; 1.05 is not a perceivable step.
- 30 of 48 screens have no loading state, 23 no error state, 33 no empty
  state, 11 no test.

---

## 1. What "transformative" has to mean, and the discipline behind it

The word the owner used is **transformative, not decorative**. The
engineering meaning:

> A screen is transformed when the *information* on it changes, not when
> the *styling* of the same information changes.

Four sourced principles this plan is held to. These are the "legit
discipline" the work must cite, and each one produces a checkable gate.

**P1 — Progressive disclosure.** Nielsen Norman Group: show the few
options most users need; defer the rest behind one deliberate step.
*Gate:* every screen states its answer above the fold; secondary detail is
one tap away, never a second scroll of equal weight.
Source: Nielsen, *Progressive Disclosure* (NN/g, 2006, rev. 2024).

**P2 — Recognition over recall.** Nielsen's Heuristic #6. An employee must
never hold a number in their head between two screens.
*Gate:* every count that matters is rendered where the decision is made,
not on the screen that owns the record.

**P3 — 8-point grid, modular type.** Material Design 3 layout
(m3.material.io/foundations/layout) uses a 4dp sub-grid / 8dp grid; Apple
HIG uses 8pt. A modular type scale (1.200 minor third, Tim Brown,
*More Perfect Type*) gives steps the eye can tell apart; 1.05 cannot be.
*Gate:* `design/gates/tokens.mjs` refuses a spacing value off 4, and a type
step outside 1.125–1.333.

**P4 — Four states, always.** Every data surface renders loading, empty,
error, content. (Scott Hurff, *Designing UI States*; Shopify Polaris and
Material both encode it.)
*Gate:* a test walks `views/` and fails any screen with a resource and
fewer than four states. Currently 33 would fail.

**P5 — Permission is the backend's answer, never the frontend's.**
The PWA never decides who may see a department. It asks, renders what it
gets, and shows a truthful empty state otherwise.
*Gate:* no role-name string literal in `views/` or `components/`.

---

## 2. Home

**Purpose:** answer "what do I do right now", in under two seconds, before
any scroll.

Order (top to bottom), each block collapsing to nothing when it has nothing:

1. **Now bar** — greeting, live site time, today's shift window
   (`19:00–03:30`), and the state word: *Not in yet · Working 6h 12m ·
   Done 8h 03m*. Today it says "Last check-out was at 08:17 pm" and makes
   the reader compute the rest.
2. **Check in / out** — unchanged mechanically, but the button carries the
   consequence: *Check out · 8h 03m today*.
3. **Needs you** — approvals. Today it renders **one** row type (remote
   check-in) because `home.needs_you` was never built. §3 of this plan
   builds it: leave, expense, OT, attendance, shift requests in one list.
4. **Announcements** — §3 below. Max 2 cards, unread first, then a link.
5. **Your requests** — bounded at 3, with a real "Show N more".

Everything else Home used to carry is now a tab. That part was right.

---

## 3. Announcements — including how HR operates it

The owner asked for help on the HR side. This is the whole workflow, and
it is deliberately boring: HR are not trained admins, and a feature they
find frightening is a feature that ships empty.

### The doctype
`HR Announcement` (new, in `hrms/`), fields:

| Field | Type | Why |
|---|---|---|
| `title` | Data, reqd | the one line in the card |
| `body` | Text Editor | sanitised through the existing `utils/safeHtml.js` |
| `category` | Select: Notice · Policy · Event · Urgent | colour + icon, nothing more |
| `publish_from` / `publish_until` | Date | it disappears on its own — nobody has to remember to delete it |
| `audience` | Select: Everyone · Company · Department · Branch | |
| `audience_value` | Dynamic Link | filled only when audience ≠ Everyone |
| `pinned` | Check | at most one pinned at a time, enforced in `validate` |
| `acknowledge_required` | Check | turns the card into "I've read this" |

Workflow: **Draft → Published**. Submit is not used; an announcement that
must be corrected should be editable, and a cancelled submitted doc is a
tombstone HR cannot clean up.

### What HR actually does
1. Desk → *HR Announcement* → New.
2. Type title and body. Pick a category. Pick who sees it.
3. Set `publish_until` (the form defaults it to +14 days — HR never has to
   think about expiry, and the board never rots).
4. Save, then *Publish*.

That is four steps and no concepts HR does not already have. No channel,
no segment builder, no scheduling engine.

### Read tracking
`HR Announcement Read` (child-free doctype: `announcement`, `employee`,
`read_on`, `acknowledged`). Written by the PWA on card expand. Gives HR
one number — *read by 31 of 44* — which is the only report they will ask
for, and the reason `acknowledge_required` is worth having for policy
documents.

### In the PWA
`home.announcements` returns at most 2 for the Home block; the full list
lives at `/announcements` (reached from the Home block and from More).
Card = category dot, title, relative date, 2-line clamp. Expanding marks
read. Unread carries a lime dot; read cards drop to secondary weight and
sort below.

**Backend cost:** 2 doctypes, 3 endpoints (`list`, `mark_read`,
`acknowledge`), one permission query. Roughly one slice.

---

## 4. Calendar

The owner: *"each date must serve function… what is going on in that date?
team roster who is off"*, per persona, **without overflowing with text**.

The answer to "without overflowing" is architectural, not editorial:
**the month grid carries DOTS, the day sheet carries WORDS.** A tile is
~44px; it can hold a number and up to three 4px dots and nothing else.
Tapping a day opens a sheet. That is P1 applied literally.

### The tile (everyone)
- Background = the day's attendance status (the existing colour legend).
- Up to 3 dots, fixed order and colour, legend at the foot of the screen:
  - **leave** — you are off
  - **holiday / rest day**
  - **event** — company event or announcement dated that day
- A small corner mark when the day needs you: an unmarked day, a missing
  punch, an unclaimed OT day.

### The day sheet (employee)
- Date, shift window, your punches as a timeline (IN 19:02 · OUT 03:28),
  total worked, and the attendance status with its reason.
- Anything actionable for that day, as a button: *Request attendance ·
  Claim overtime · Request leave*, pre-filled with the date.
- Holiday / leave named plainly.

### The day sheet (approver — adds a section)
- **Who is off** in their reporting line that day: name, leave type,
  half-day marker. Names only, no reasons — a leave reason is private.
- **Requests dated this day waiting on them**, tappable straight to the
  decision.

### The day sheet (manager / department head — adds)
- **Roster coverage**: *Production · 12 of 15 in · 2 on leave · 1 unmarked.*
  One line per department they own. This is the number a manager opens a
  calendar for and today has no way to get without Desk.

### Persona resolution
One endpoint, `calendar.day(date)`, returns only the sections the caller
is entitled to — the server decides from reports-to and department
permissions (P5). The PWA renders sections that arrive. No role strings in
the frontend, and no employee can enumerate a department by tampering.

**Backend cost:** `calendar.month(dots)` + `calendar.day(date)`. One slice
each; the month endpoint is mostly a reshape of queries the dashboard
already runs.

---

## 5. Requests

The owner: *"better info of the employee itself always prioritise…
kinda like a counter of everything related to request stuff, remaining
stuff."* That is P2 exactly — the balance belongs where the decision is
made, not on the screen that stores it.

Top of the screen, a **balance strip** before any tile:

- **Leave** — per type, `12.5 of 16 left`, with a bar. Expiring-soon
  carries a date.
- **Overtime** — `6 days unclaimed` (the Unclaimable Days work already
  computes this) and `RM 340 approved, unpaid`.
- **Expenses** — `RM 120 awaiting approval`.
- **Attendance** — `2 days unmarked` — the single most common cause of a
  wrong payslip, and today invisible until payroll.

Each stat is a filter: tapping "2 days unmarked" opens the list already
filtered, never a fresh search.

Below: the existing START A REQUEST tiles, then the request list with
status chips. Tiles keep their current grid; they are the one part of the
app that already works.

**Backend cost:** one endpoint, `requests.summary`, returning the five
numbers. Everything in it is already computed somewhere.

---

## 6. Score

The empty screen. Fixes, in order:

1. Title reads **Score** (defect, §0).
2. The empty state stops being the page. When there is no appraisal, the
   screen still shows: the current cycle and its dates, who the appraiser
   is, and what happens next — *"Your review opens 1 Oct. Nothing for you
   to do yet."* An employee's real question is "am I late for something",
   and a dashed box does not answer it.
3. When there IS an appraisal: the score ring, per-KPI rows with target vs
   actual, and the cycle history as a sparkline. This already exists in
   `KpiDetail` — it is the empty path that is unbuilt.
4. Feedback and goals, if the site uses them, as two collapsed sections.

**Backend cost:** one field added to the existing dashboard payload (the
next cycle's dates). Not a new endpoint.

---

## 7. Helpdesk, Team, SOPs, Profile

**Helpdesk** — already one page with two pills (HR Issues · IT Helpdesk);
the structure the owner asked for is shipped. What it needs: each pill
showing *your* open count, a two-line "what to ask here" under each, and
the HR contact list folded in so an employee never leaves to find a name.

**Team** — the permission rule is the feature (P5). The list shows exactly
what the server returns for the caller: their own department, or their
reporting line, or more. No role literal in the frontend. When the server
returns nothing, the screen says *"Your role does not include the team
directory"* — truthful, not a spinner that never resolves. Per person:
name, role, department, today's status (in · on leave · off), and tap to
call or message. Contact detail is server-gated the same way.

**SOPs** — search first (it is a lookup tool, not a browse tool), category
chips, and a "recently updated" row. `SopList` carries 20 of the 103
arbitrary pixel values; it is the worst offender and gets rebuilt on the
grid.

**Profile / Settings** — today a long undifferentiated list. Reshape into
four groups: **You** (photo, name, ID, join date, shift), **Work**
(department, reports to, company — read-only, sourced), **App**
(language, theme, notifications, text size), **Account** (password, sign
out, version + build). Add: an "About this app" row showing the build
string, because every phone-side defect this month began with "which
version are you on".

---

## 8. The visual system — the part that makes it LOOK different

None of §2–§7 changes how the app looks. This section does.

**V1 — 4pt grid.** Every spacing and radius token becomes a multiple of 4.
The 14 current values collapse to `4 8 12 16 20 24 32 40 48`. Five tokens
that are all 10px become one.

**V2 — modular type, ratio 1.200.** `12 · 14 · 17 · 20 · 24 · 29 · 35`
(minor third from a 14px body). Body text never below 14px; the 16px
input-font rule stays (iOS zoom).

**V3 — the 103 arbitrary values go.** Each is replaced by the nearest
token; `design/gates/lint.mjs` gains a rule that fails a new one.

**V4 — density.** Current list rows are ~64px with 20px gaps. Target: 56px
rows, 8px gaps, dividers instead of gaps inside a group. On a 390×844
phone this is roughly **three more rows visible per screen**, which is the
difference between "sparse" and "an app".

**V5 — the empty-black problem.** A screen whose content ends above the
fold gets a closing block rather than void: on Score the next cycle, on an
empty list the primary action. Nothing decorative — a filler card is worse
than black.

**Cost, honestly:** V1–V4 re-shoot all 114 visual baselines, which needs a
running site. `~/verify-bench/apps/hrms` symlinks this worktree and
`spoke.localhost` has 31 employees, so this is available — it was believed
unavailable for five releases and it was one `ls` away.

---

## 9. Rules this plan changes (the owner's explicit authority)

**R1 — "no new backend in 2.0" is withdrawn.** Source: old plan §7. It
made every transformative item unbuildable and is the root cause of §0.
Announcements, `home.needs_you`, `calendar.day`, and `requests.summary`
are in scope. The original constraint the owner set was *no Desk work*;
`hrms/api/` is the PWA's own backend and was already amended in.

**R2 — a slice that changes only strings is not a slice.** New gate: a
2.0 slice must change at least one of {information rendered, layout,
token}. A pure rename ships as `chore:` and does not count against the
plan.

**R3 — tokens are validated, not just generated.** `design/gates/` gains
`tokens.mjs`: 4pt grid, type ratio band, no duplicate values under
different names.

**R4 — four states are a gate, not a guideline.** P4 above. 33 screens
currently fail; the gate starts as a ratchet (no new failures) and the
backlog is burned down per page.

**R5 — the spec follows the code on renames.** The two page titles in §0
are the evidence: a rename that touches one of {nav, page title, spec}
must touch all three. One test, `naming-consistency.test.js`.

---

## 10. Order of work

Each row is one commit with its own tests.

| # | Slice | Kind | Depends |
|---|---|---|---|
| A1 | The two page titles + naming gate (R5) | fix | — |
| A2 | `tokens.mjs` gate + 4pt grid + modular type (V1,V2) | refactor | A1 |
| A3 | 103 arbitrary values → tokens, lint rule (V3) | refactor | A2 |
| A4 | Density pass on lists (V4) | refactor | A2 |
| A5 | Four-states ratchet (R4) + Score's real empty path (§6) | feat | — |
| B1 | `HR Announcement` doctypes + 3 endpoints | feat | — |
| B2 | Announcements in the PWA: Home block + list page | feat | B1 |
| B3 | `home.needs_you` — all five request types | feat | — |
| C1 | `requests.summary` + the balance strip (§5) | feat | — |
| C2 | `calendar.month` dots | feat | — |
| C3 | `calendar.day` sheet, employee sections | feat | C2 |
| C4 | Day sheet, approver + manager sections (P5) | feat | C3 |
| D1 | Home "Now bar" (§2) | feat | — |
| D2 | Team, server-gated (§7) | feat | — |
| D3 | Helpdesk counts, SOP search, Profile grouping (§7) | feat | A2 |
| E1 | Re-shoot 114 baselines on `spoke.localhost` | chore | A4 |

A1–A5 are what makes it look different. B–D are what makes it worth
opening. E1 closes the debt that has been owed since the 9 Sep audit.

---

## 11. What I need a ruling on

1. **Announcements authorship** — HR Manager only, or any HR User?
2. **Acknowledgement** — is "I've read this" wanted for policy items, or
   is read-tracking enough?
3. **Manager coverage line** — may a department head see *who* is off, or
   only the count? (Leave reasons are never shown either way.)
4. **Density (V4)** — 56px rows is a real change to how the app feels.
   Worth one screenshot round before A4 lands.

---

## 12. Rulings received, 22 September 2026

**Q1 — Announcements authorship: ANY HR USER.**
Permission is `HR User` create/write, `Employee` read through the API only.
No Desk read for staff. One consequence worth naming: any HR User can post
to Everyone, so the post carries `owner` and is shown to HR in the list —
accountability by attribution, not by approval. No maker-checker workflow;
it would stop the feature being used.

**Q2 — What acknowledgement is.**
Two different things, and the difference matters:

- **Read tracking** (always on, silent): the PWA records that you opened
  the card. HR gets *"read by 31 of 44"*. You do nothing; you are not
  asked anything.
- **Acknowledgement** (`acknowledge_required`, off by default): the card
  grows a button — **"I've read and understood this"** — and stays pinned
  at the top of your Home until you press it. It writes your name and the
  timestamp. It is the difference between *"we published it"* and *"she
  confirmed she read it on 3 Oct at 09:12"*, which is what a policy or a
  safety notice needs and a canteen-closed notice does not.

**Ruling taken:** build both. Read tracking always; the button only when
HR ticks the box. HR sees who has not acknowledged, as a list of names.

**Q3 — Manager coverage: YES, names are allowed.**
A department head sees *who* is off, not only the count. Bounded by two
rules that are not negotiable:
- **Leave REASON is never shown** to anyone but the employee and the
  approval chain. Type ("Annual Leave") yes; reason no.
- The list is whatever the server returns for that caller (P5). A manager
  sees their departments; nobody enumerates another.

**Q4 — Density: measured, not guessed (see §13).**

**Q5 (new) — KPI/Score visibility is a protected boundary (see §14).**

---

## 13. Density — the real method

"How dense" is not a taste question; it has an established answer.

**The constraint that is fixed:** a tap target is **44×44pt** (Apple HIG,
Accessibility → Buttons and Controls) / **48dp** (Material 3, minimum
touch target). That is the floor and it does not move. Body text stays
≥ 14px (P3) with a 1.5 line-height for readability (WCAG 2.1 SC 1.4.12,
Text Spacing).

**What actually shrinks** is the space *between* rows, not the rows:

| Today | Target | Where the number comes from |
|---|---|---|
| row height ~64px | **56px** | 44px target + 2×6px padding = 56. Still above both platform floors. |
| gap between rows 20px | **0**, with a 1px divider | Material list spec: items in a group are separated by dividers, not by gaps. Gaps mean "different group". |
| gap between groups 20px | **24px** | 4pt grid, one step above the in-group spacing so grouping is legible. |
| section padding 28px | **24px** | same grid |

**Measured effect** on a 390×844 phone (usable ≈ 640px after header, tab
bar and safe areas): today 640 ÷ (64+20) = **7.6 rows**. After:
640 ÷ (56+1) = **11.2 rows**. Three to four more rows per screen, with no
target smaller than the platform minimum.

**How it gets signed off, so nobody has to guess:** slice A4 ships as a
before/after screenshot pair on three widths (360, 390, 430) before it is
merged. That is the "screenshot round" — it costs one capture run, and
`~/verify-bench` with `spoke.localhost` can produce it.

**What density must never buy:** a target below 44px, body text below
14px, a contrast below 4.5:1, or a focus ring that no longer clears the
row. All four are already gates.

---

## 14. Score / KPI — the protected boundary

This is the highest-risk surface in the app. A performance score leaking
to the wrong person is not a UI bug; it is a personnel incident. The
revamp must not widen it by one row, and §6's visual work sits strictly
inside the existing fence.

### What the fence is today (verified in `hrms/api/kpi.py`)

`_scope(user)` is **the one place** that answers "who is this caller and
whose rows may they see". It returns a tier plus the employees it admits:

| Tier | Who | Admits |
|---|---|---|
| `hr` | `is_hr_operator(user)` — by ROLE only | everyone |
| `ceo` | own Employee's designation == `CEO_DESIGNATION` | everyone |
| `manager` | reporting chain via `get_allowed_appraisal_employees` | their chain only |
| `self` | `employee in own_employees(user)` | themselves |
| `None` | everyone else | nothing |

Three properties that must survive the revamp, each already load-bearing:

1. **HR is decided by role and only by role**, answered before the
   identity gate — so an HR account with no Employee row still works
   (new hire, shared login, Administrator during support).
2. **CEO and manager are identity-gated first, fail-closed.** No Active
   Employee → no tier. That is what closes the duplicate-Employee-row
   forgery path.
3. **The department tree is `ceo` + `hr` ONLY** (`kpi.py:722`). A manager
   never sees structure, only people. Their tab is labelled "My Team" for
   exactly that reason.

And the rule that keeps it honest: **`can_view_team_kpi()` is a NAV gate,
not a data gate.** It decides whether a tab is drawn. Every read
re-derives the tier through `_scope`, and `_require_kpi_read` re-checks
before a single KRA row is loaded. Two answers to "may I see this person"
is precisely how the filing guard and the row scope once disagreed
(`.claude/plans/family.md`).

### Rules this revamp binds itself to

- **KR1 — No new KPI endpoint.** The Score work in §6 reads the payload
  `get_my_kpi_dashboard` / `get_team_kpi` already return. Nothing new is
  exposed.
- **KR2 — The frontend never decides.** No role literal, no designation
  string, no "if HR" in `views/kpi/`. It renders the sections the server
  sends. Enforced by P5's gate.
- **KR3 — Empty is not a leak.** §6 adds cycle dates and the appraiser's
  name to the empty path. Both are about the READER's own cycle and come
  from the same fenced payload. No other person's data enters an empty
  state, ever.
- **KR4 — Density and tokens do not touch scope.** A4/A2 change CSS in
  `KpiDetail`; they may not touch a `v-if` that gates a section.
- **KR5 — A guard test, committed with A5.** `test_kpi_fence.py` asserts,
  on a site: a tierless user gets no tab AND is refused the detail; a
  manager is refused an employee outside their chain; a manager is refused
  the department tree; HR without an Employee row keeps the tab. Four
  assertions, and they fail if anyone widens the fence later.
- **KR6 — Screenshots are a leak vector.** The baseline re-shoot (E1) runs
  as a tierless persona plus `self` only. No team baseline is captured;
  114 PNGs of somebody's real appraisal do not belong in the repo.

---

## 15. Every screen — nothing left alone

All 48. `states` = which of loading / empty / error / content are missing
today. Slice column maps to §10.

### Primary destinations

| Screen | What it becomes | States | Slice |
|---|---|---|---|
| `Home.vue` | Now bar · check in/out · Needs you · Announcements · Your requests (§2) | — | D1, B2, B3 |
| `attendance/Dashboard.vue` | Calendar. Title fixed. Dots on tiles, day sheet on tap (§4) | empty | A1, C2, C3, C4 |
| `Requests.vue` | Balance strip above the tiles (§5) | loading, empty | C1 |
| `kpi/Dashboard.vue` | Score. Title fixed. Real empty path (§6, §14) | — | A1, A5 |
| `More.vue` | Grouped, with counts on Helpdesk and SOPs | — | D3 |

### Attendance family

| Screen | What it becomes | States | Slice |
|---|---|---|---|
| `EmployeeCheckinList.vue` | Grouped by day with a per-day total; a missing-punch row is flagged, not silent | error | A4, A5 |
| `AttendanceRequestList.vue` | Status chips, date-filtered from the balance strip | empty, error | A5, C1 |
| `AttendanceRequestForm.vue` | Pre-fills the date when opened from a day sheet | error | C3 |
| `ShiftAssignmentList.vue` | Shows the window (`19:00–03:30`), not just the name | empty, error | A5 |
| `ShiftAssignmentForm.vue` | Read-only detail; density pass | — | A4 |
| `ShiftRequestList.vue` | Chips; merged into the Requests list feed | empty, error | A5 |
| `ShiftRequestForm.vue` | Allowlist already done; density + 4 states | error | A4, A5 |

### Leave

| Screen | What it becomes | States | Slice |
|---|---|---|---|
| `leave/Dashboard.vue` | Balance per type with expiry dates — the source of the Requests strip | empty | C1, A5 |
| `leave/List.vue` | Chips, grouped by status; approver name on pending rows | error | A4, A5 |
| `leave/Form.vue` | Allowlist done; add remaining-balance inline as you pick the type (P2) | error | C1 |

### Expenses

| Screen | What it becomes | States | Slice |
|---|---|---|---|
| `expense_claim/Dashboard.vue` | Totals: awaiting / approved-unpaid / paid this period | empty | C1 |
| `expense_claim/List.vue` | Amount right-aligned, chip, grouped by month | error | A4 |
| `expense_claim/Form.vue` | Allowlist done; running total as rows are added | error | A5 |

### Overtime

| Screen | What it becomes | States | Slice |
|---|---|---|---|
| `ot/OTRequestList.vue` | Hours + the money it becomes; unclaimed days surfaced | empty, error | C1, A5 |
| `ot/OTRequestForm.vue` | Pre-fill from a calendar day; show computed hours before submit | error | C3 |
| `ot/ReplacementLeave.vue` | Balance + expiry, same shape as leave | empty | C1 |
| `ot/ReplacementLeaveClaimForm.vue` | Density + 4 states | error | A4, A5 |

### Approvals

| Screen | What it becomes | States | Slice |
|---|---|---|---|
| `RemoteApprovals.vue` | Stays remote-only, but gains the count in its header and the density pass | error | A4 |
| — *(new)* | The unified queue `home.needs_you` feeds — all five request types, decided in place | all | B3 |

### Helpdesk & issues

| Screen | What it becomes | States | Slice |
|---|---|---|---|
| `helpdesk/HelpdeskHub.vue` | Two pills with YOUR open count each, one line of "ask here when…", HR contacts folded in | empty | D3 |
| `helpdesk/HelpdeskList.vue` | Status chips, last-reply time (not created time — the useful one) | empty, error | D3, A5 |
| `helpdesk/TicketDetail.vue` | Thread reads as a conversation, newest last, your replies aligned | error | A4 |
| `helpdesk/TicketNew.vue` | Category first, then one field. Density | error | A5 |
| `issues/HRIssueBoard.vue` | HR-only (already fenced). Density + counts per column | error | A4 |
| `issues/IssueList.vue` | Chips, grouped | empty, error | A5 |
| `issues/IssueForm.vue` | 4 states | error | A5 |
| `issues/IssuesTab.vue` | Folds into the hub; no second entry point | — | D3 |

### Team

| Screen | What it becomes | States | Slice |
|---|---|---|---|
| `team/TeamDashboard.vue` | Server-gated. Today's status per person; truthful refusal when not entitled (§7, P5) | all | D2 |
| `team/TeamRoster.vue` | Who is in / off today, by department the server allows | empty, error | D2 |

### SOPs

| Screen | What it becomes | States | Slice |
|---|---|---|---|
| `sop/SopList.vue` | **Rebuilt** — search first, category chips, recently-updated row. Worst offender: 20 of the 103 stray pixel values | empty, error | A3, D3 |
| `sop/SopDetail.vue` | Readable long-form: 16px body, 1.6 line-height, sticky section nav | error | A4 |
| `sop/SopFormSheet.vue` | Density + 4 states | error | A5 |

### Account & shell

| Screen | What it becomes | States | Slice |
|---|---|---|---|
| `Profile.vue` | Four groups: You · Work · App · Account (§7). 17 stray pixel values go | — | A3, D3 |
| `AppSettings.vue` | Folds into Profile → App. Add text size + build string | — | D3 |
| `ChangePassword.vue` | Strength feedback, 4 states | error | A5 |
| `Notifications.vue` | Grouped by day, unread first, mark-all-read | empty, error | A5 |
| `HRContacts.vue` | Folds into the Helpdesk hub; kept as a route | empty | D3 |
| `More.vue` | See primaries | — | D3 |
| `Login.vue` | Density + error clarity; never says "invalid" without saying what to do | — | A4 |
| `InvalidEmployee.vue` | Says who to contact, from HRContacts data | — | D3 |
| `NotFound.vue` | One action back to Home | — | A4 |

### Infrastructure (no user-facing change, but in scope)

| File | What it becomes | Slice |
|---|---|---|
| `FormShell.vue` | Carries the 4-state contract so forms inherit it instead of each rebuilding it | A5 |
| `TabbedView.vue` | Density tokens | A4 |
| `kpi/KpiDetail.vue` | Tokens + density ONLY. No `v-if` on a gated section may change (KR4) | A2, A4 |
| `DesignSpecimen.vue` | Regenerated from the new tokens; it is the visual proof A2 landed | A2 |
| `components/glass/*` (47) | Re-tokenised against the 4pt grid and the modular scale | A2, A3 |
| `SideNav.vue` | 13 stray pixel values go | A3 |

**Count check:** 48 screens listed. 33 gain at least one missing state,
which closes P4's backlog entirely rather than ratcheting it.

---

## 16. Revised order of work

Unchanged from §10 except for what the rulings added:

| # | Slice | Kind | New? |
|---|---|---|---|
| A1 | Two page titles + naming gate | fix | |
| A2 | `tokens.mjs` gate, 4pt grid, 1.200 type | refactor | |
| A3 | 103 stray values → tokens + lint rule | refactor | |
| A4 | Density pass, **screenshots at 360/390/430 before merge** | refactor | Q4 |
| A5 | Four states across 33 screens + Score's empty path | feat | |
| A6 | **`test_kpi_fence.py` — the four-assertion guard (KR5)** | chore | Q5 |
| B1 | `HR Announcement` + `HR Announcement Read`, 3 endpoints, **any HR User** | feat | Q1 |
| B2 | Announcements in the PWA, **read tracking + acknowledge button** | feat | Q2 |
| B3 | `home.needs_you` — five request types | feat | |
| C1 | `requests.summary` + balance strip | feat | |
| C2 | `calendar.month` dots | feat | |
| C3 | `calendar.day`, employee sections | feat | |
| C4 | Day sheet approver + manager, **names allowed, reasons never** | feat | Q3 |
| D1 | Home Now bar | feat | |
| D2 | Team, server-gated | feat | |
| D3 | Helpdesk / SOP / Profile / More consolidation | feat | |
| E1 | Re-shoot 114 baselines, **tierless + self personas only (KR6)** | chore | Q5 |

A6 runs before anything touches `kpi/`, so the fence is pinned before the
revamp goes near it.

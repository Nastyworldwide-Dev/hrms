# Nadi PWA UX 2.0 — review and delivery plan

Status: proposal for review, 8 September 2026. No application code changed.
Branch `nz-glass` at `550771c6f`. Inputs: `Nadi PWA UI UX 2.0/` (prototype +
mapping), the shipped `frontend/` and `hrms/api/`, the 7 Sep Nadi audit, the
8 Sep 360 audit and its status ledger, the compact UX proposal (7 Sep), the
phase 9 work order (44 routes, 18 sheets, six states) and the Glass spec v1.1.

The ask: make the UX justified at every part, close every gap and hole, and
have the UI ride the correct flow. This document turns that into a checkable
contract, a gap ledger against what is already shipped, the decisions that
block the build, and an ordered slice plan. Its companion,
[NADI_2.0_SURFACE_MAP.md](NADI_2.0_SURFACE_MAP.md) (9 Sep), carries the measured
numbers: every route and sheet, the grid, the scroll budget, the redundancy census.

> **AMENDED 10 Sep 2026 — not yet approved.** Decision Q0 below (retire Liquid
> Glass) is **reversed** by
> [NADI_2.0_AMENDMENT_A_LIQUID_GLASS.md](NADI_2.0_AMENDMENT_A_LIQUID_GLASS.md),
> which keeps Glass on chrome only, adds U16-U18 (glass placement,
> reachability, readability floor) and moves accessibility from phase 4 to a
> required gate in phase 0. Read the amendment before acting on §5 Q0, §6
> slice 0.6, or surface map §1.3.

---

## 0. What the folder contains

| File | What it is | Size |
|---|---|---|
| `nadi-prototype.html` | One-file click-through. 31 screens, 5 sheets, 5 tabs, sample data for one persona (Nik, an approver) with a staff/approver toggle. Ends with a "Flow map" screen that lists the decisions it takes. | 2,293 lines |
| `nadi-erpnext-mapping.md` | Every prototype screen pinned to a doctype, written against **vanilla ERPNext v15 + hrms v15**. Names five custom items, a config-not-code list, six likely bug sources, a verify-on-instance checklist and a travel-money addendum. | 16 KB |

The prototype's own summary of what it changes (its Flow map screen):

- Home has no quick links; every one duplicated a tab. Home shows what needs you.
- One "New request" sheet routes to the right form with the type preset.
- Attendance is a calendar; one request list with chips replaces four empty sections.
- Requests holds leave and expenses together: same object, different fields.
- Approvals is a header icon and a "Needs you" list, not a page inside More.
- Expenses lost its tab; it is a request type.
- Every empty state is one line. Status words are fixed: draft, pending, approved, rejected, withdrawn.

---

## 1. Verdict

**The prototype is a restructure, not a reskin.** It changes where things live
and why, fixes the lifecycle of a request end to end, and adds five new domains
(travel, assets, training and certifications, company events, SOP
acknowledgement). Measured against the shipped app:

| Share | Kind of work | Examples |
|---|---|---|
| ~55% | Re-routing screens and data we already have | calendar, leave balances, claims summary, team, roster, KPI, SOPs, issues, geofence review, holidays, withdraw |
| ~25% | Lifecycle and state work the audits already demanded | six states per surface, done screen, progress timeline, pending state after Approve, plain-language errors, notification copy, offline |
| ~20% | New features needing doctypes and HR policy | travel in the PWA, asset request, employee certification, SOP acknowledgement, events, nudge approver |

**The mapping document is right about the shape and wrong about this fork in
eight places** (section 4). It assumes vanilla v15. We run a Frappe 16 fork
that already has OT Request, Replacement Leave Claim, Remote Checkin Request,
Shift Location rules, a 70/20/10 appraisal with grade and PIP fields, SOP
Document, Employee Issue and native Helpdesk. Two of its five "custom" items are
genuinely missing: Asset Request and Employee Certification.

**The prototype competes with the compact proposal of 7 September** on one
point only: the tab bar. Compact says Attendance · Leave · Home · Expenses ·
Assets. The prototype says Home · Calendar · Requests · Score · More. Everything
else in the compact proposal (one issue system, assets as a real feature, Home
shows summaries not shortcuts, density rules) is reinforced by the prototype.
Decision Q1 below settles the tab bar; the rest of the compact proposal folds
into this plan.

---

## 2. The UX contract

"Justified at every part" has to be checkable or it is a mood. These twelve
rules are what the prototype encodes plus what the audits proved was missing.
Each carries the gate that catches a breach. Rules marked **G** get a machine
gate; rules marked **R** are checked in review with a fixture screenshot.

| # | Rule | Why (evidence) | Gate |
|---|---|---|---|
| U1 | Every screen has one job and one primary action. Secondary actions are ghost buttons. Nothing on a screen duplicates a tab. | Home today has seven quick links that mirror the tab bar; More is 62% empty (work order §3.1 J5). | R: screen ledger column "primary action" filled for every route. |
| U2 | Every surface shows all six states: loading (skeleton), empty (one line, no dashed box), error (says it failed, never "nothing here"), offline, permission denied (plain language), pending (after a slow or destructive tap). | FormView has no skeleton or error; RequestPanel turned a 403 into "Nothing here yet" (audit F2); no offline state anywhere (F3, work order §3.3). | **G**: `test_pwa_resource_states.py` extended to every container; coherence spec captures each state from a fixture. |
| U3 | Every request type has the same lifecycle surface: type sheet → form with a "what happens next" summary (days, balance after, approver, paid with) → done screen (View request / Done) → detail with a progress timeline (submitted → waiting on X → outcome) → decision notification → history. | Today a Save lands on a raw detail form; history excludes OT, attendance and RL on a stale premise (pwa-deep, RequestPanel:108). | **G**: one table test per request type against the lifecycle contract (route exists, summary fields present, timeline steps present). |
| U4 | Fixed vocabulary. Requests: Draft, Pending, Approved, Rejected, Withdrawn. Money adds Awaiting payroll, Paid. No doctype names and no document names in employee-facing copy. | "raised a new Leave Application for approval: HR-LAP-2026-02660" (mapping §2); expense claim has four names on one screen (work order row 38); permission failures name doctypes (row 39). | **G**: copy lint over i18n source strings: rejects `[A-Z]{2,}-[A-Z]{3}-\d{4}`, a doctype-name list, and "Submit" as a status. |
| U5 | Home = today + what needs you. "Needs you" shows at most three rows then "N more". Nothing else. | Prototype Home; audit finding that Home's request panel hides failures. | R + U2 gate. |
| U6 | Notifications are a log of what happened. Anything needing a decision also lives on Home and in Approvals. Quiet by default: a check-in inside the radius or covered by approved travel never notifies, and the count of quiet clears is shown. | The 134-notification screen (mapping §5.5); N01–N09 in the notification audit. | **G**: producer tests assert no PWA Notification for an in-radius punch; feed shows the quiet count. |
| U7 | The calendar day is the pivot. Every day state (present, half, absent, leave, travel, training, rest, open request) opens a sheet with exactly the actions that make sense that day. | Prototype day sheet; today the calendar is read-only and the correction form is three taps away. | R: day-state → action matrix in the coherence fixture. |
| U8 | An approver sees context before deciding: the person's balance, cover on that day, how old the request is. Tapping Approve shows a pending state until the row is gone. | Work order J4: no loading state between Approve and the row disappearing; PWA1/PWA2 capability mismatch (fixed in 6384996d6, keep it). | R + U2 pending state. |
| U9 | Balances, totals and hours come from the server ledger. The app never computes a balance. Client-side checks only warn; the server decides. | mapping §2 Leave; `decisions/leave-insufficient-balance.md`; OT readers disagreeing (360 §4). | **G**: no arithmetic on balance fields in `frontend/src` (lint rule on `leave_balance`, `total_leave_days`). |
| U10 | Plain language. Every number has a unit and, where it is not ours, a source ("from HR records", "from the IT asset register"). | Prototype footers; work order 9.7c. | R. |
| U11 | Read/write follows ownership. The app reads assets, certifications, KPI figures and roster; it writes requests only. | mapping §5.3 two sources of truth; Verifica cutover rules. | **G**: API allowlist test: no `insert`/`set_value` on Asset, Employee, Appraisal from PWA endpoints. |
| U12 | Multi-company fence on every new endpoint. | mapping §5.6; `allowed_companies()` in `hrms/overrides/company_scope.py` for API reads, `fenced_companies()` in `hrms/utils/report_scope.py` for reports; R1 decision. | **G**: AST test that every new whitelisted function calls the fence helper (pattern already used for sync endpoints). |
| U13 | Scroll budget: a tab-root screen fits the fold (≤ 752 px at 390×844) in its resting state; sheets ≤ 720; a form's first field is above the fold and its primary action is sticky. | Surface map §2: Home 1382, Calendar 1362, Requests 1301, Notifications 1366 today. | **G**: `frontend/e2e/app-measure.mjs` against the seeded site. |
| U14 | One spacing scale (4, 8, 12, 16, 24, 32) and twelve type roles; no arbitrary bracket values. | Surface map §5: 265 distinct classes, 39 arbitrary. | **G**: the spacing census script. |
| U15 | One row, one pill: every list row is `RequestRow`, every status string comes from `StatusPill`. | Nine `*Item.vue` components and 13 inline status labels today. | **G**: grep gate. |

These rules become spec addendum §17 and the coherence gate's rule list.
A slice that breaks a **G** rule cannot commit; a slice that breaks an **R** rule
cannot pass review.

---

## 3. Gap ledger — prototype against the shipped app

Gap type: **R** reroute or recompose what exists · **S** state or lifecycle work
· **N** new feature · **P** policy decision needed first.

### 3.1 Shell and Home

| Prototype | Today | Gap | Backend | Note |
|---|---|---|---|---|
| Tabs Home · Calendar · Requests · Score · More | Home · Attend · Leaves · Expenses · More (`data/navItems.js`) | R + **P (Q1)** | none | Five fixed tabs stay (Ionic stacks). Old routes keep working with redirects. |
| Header: bell with badge, approvals icon with badge (approvers only), avatar | Bell exists; approvals via More and a Home banner | R | `get_unread_notifications_count`, pending count needs the unified queue (3.5) | |
| Greeting + date | none | R | `get_current_employee_info` | |
| Check-in card: state, shift and location, one CTA | `CheckInPanel` | S | `remote_checkin.punch`, `geofence.*` | Add "punched, pending" state, offline state, strict-block exit into a prefilled correction. |
| "Needs you": approvals, geofence reviews, issue replies, SOPs to read, certs expiring; 3 rows then "N more" | `PendingApprovalsBanner` + `RequestPanel` | S, later N | new `home.needs_you` aggregator | SOP and cert rows arrive with 3.x. |
| "Coming up at work" events carousel | none | **N + P (Q6)** | Event doctype or M365 | One source, not both. |
| "Your requests" two rows | `RequestPanel` (10 rows, three types) | S | existing list APIs | Include OT, attendance, RL. |

### 3.2 Calendar (today: Attendance)

| Prototype | Today | Gap | Backend | Note |
|---|---|---|---|---|
| Month grid with dots: present, half, absent, leave, travel, training, rest; ring for open request; legend; stats strip | `attendance/Dashboard.vue` calendar with Present / Absent / Half / Leave | S, travel and training **N** | `get_attendance_calendar_events` (+ open-request overlay, holidays) | Per-month ownership already landed (826b17e0d). |
| Day sheet with contextual actions (correction, claim OT, apply leave, claim rest day, view request, team that day) | none | S | existing forms with prefill; `team.get_team_status(date)` | Prefill contract per form (date, type). |
| "Coming up" travel rows | none | N | Travel Request | With 3.6. |
| Clock-in history grouped by day with missing-punch flag and stats | `/employee-checkins` raw IN/OUT rows | S | `get_attendance_calendar_events` + checkins | Missing OUT → correction prefilled. |
| Month navigation | "Change" is a stub in the prototype | S | already per-month | |

### 3.3 Requests hub and forms

| Prototype | Today | Gap | Backend | Note |
|---|---|---|---|---|
| Hub cards: annual balance, claims money, assets, issues, trips and training; sticky "+ New request" | Leave dashboard, expense dashboard, issues list | R, assets/trips N | `get_leave_balance_map`, `get_expense_claim_summary` | |
| New request sheet: six leave types with balances, expense, OT, shift, correction, travel, asset, training, issue | `QuickLinks` (7) | R | `get_leave_types` + balance map; `Leave Type.is_lwp` for "Unpaid" | Headcount stays out (mapping agrees). |
| Leave balances: breakdown entitlement / carried / lapsed / taken / available; other types as tiles; "worked a rest day?" | Balance cards only | S | new `get_leave_ledger_breakdown(employee, leave_type)` from Leave Ledger Entry | Read-only ledger view (U9). |
| Leave form: type preset with balance, per-type mandatory document, birthday fixed to DOB, unpaid warning, half-day segmented control, summary (days, balance after, approver) | `leave/Form.vue` on generic `FormView` | S + **P (Q4)** | `get_number_of_leave_days`, `get_leave_balance_on`, `get_leave_approval_details`; custom field `requires_document` on Leave Type + one validate hook | Client check warns only (U9). |
| Expense form: amount first, category sheet, "part of a trip", receipt required, "reimbursed with X payroll" | `expense_claim/Form.vue` multi-line generic | S + **P (Q5)** | `get_expense_claim_types`; payroll date source | Single line is a simplification; decide. Trip link needs 3.6. |
| Generic form for OT, shift change, correction, issue: date, times, reason, "goes to" | `OTRequestForm`, `ShiftRequestForm`, `AttendanceRequestForm`, `IssueForm` | S | existing | Keep OT's auto-populated hours (GOLIVE OT v2). Summary block shared. |
| Claim replacement day | `ReplacementLeaveClaimForm` | R | existing | Keep ours, not Compensatory Leave Request (hub-granted RL, ratio setting). |
| Done screen: View request / Done | none (lands on detail) | S | none | |
| Request detail: summary card, progress timeline, nudge approver, report an issue, withdraw sheet with consequence | `FormView` detail; `withdraw_request` exists | S; nudge **N + P (Q9)** | timeline from status + approval log; `withdraw_request` | Rejected doc must not render live fields (work order row 37). |

### 3.4 Approvals and team

| Prototype | Today | Gap | Backend | Note |
|---|---|---|---|---|
| Approvals: Waiting on you / Decided by you; count and oldest age; geofence group; cards with in-place Approve / Reject; Approve all leave | `RemoteApprovals` (geofence only) + per-document `RequestActionSheet` | S + **N**: unified queue | new `approval.list_pending_for_user` over all six types + remote check-ins, built on `can_decide` (6384996d6) | Approve-all is **P (Q2)**. |
| Approval detail: person, request, when, their balance, note, cover that day (team in/away, department peers) | `RequestActionSheet` decision only | S | `team.get_team_status(date)`, `get_leave_balance_map(employee)` | |
| Reject sheet with reason ("they see your reason") | reason field exists | R | existing | |
| Geofence review: Accept / Query it; cleared rows dimmed; auto-clear when approved travel covers the day | Approve / Reject + remarks | R; auto-clear N with 3.6 | `remote_checkin.*` | |
| Team day view by department with on-shift / away / off / not-in counts | `/team` `TeamDashboard` | S | `team.get_team_status` | Empty state when the caller manages nobody (row 13). |
| Week roster grid with cover-by-day flags (opener + closer) | `/team/roster` | S + **P (Q7)** | `roster.*` | Cover rule per outlet. Shift overlap error must be legible (mapping §5.4). |

### 3.5 Money, assets, travel, training

| Prototype | Today | Gap | Backend | Note |
|---|---|---|---|---|
| Claims: owed / awaiting payroll / pending / reimbursed this year; "paid with the 25 Sep payroll"; every claim with chips | `expense_claim/Dashboard.vue` summary | S | `get_expense_claim_summary`; status map Unpaid → Awaiting payroll | Trip-linked claims excluded from "owed" (mapping §7). |
| Trip money: budget, advance, unclaimed | none | N with 3.6 | Travel Request Costing, Employee Advance | Custom link `travel_request` on Expense Claim. |
| My assets, asset detail, report an issue, request handover | none | **N + P (Q3)** | ERPNext Asset (custodian), Asset Movement; Vehicle is ERPNext's, verify installed | Read-only register first. |
| Asset request form | none | **N + P (Q3)** | new `Asset Request` doctype → Asset Movement on approval | Compact proposal §Assets already scoped this. |
| Travel request form; travelling on own and team calendar; "shows as travelling, not leave" | none | **N + P (Q5)** | Travel Request + Itinerary + Costing + Employee Advance (all present) | Attendance as On Duty is a policy choice. |
| Training: certifications with expiry, completed training, training request | none | **N + P (Q8)** | Training Event / Result (present); new `Employee Certification` child table + daily expiry scheduler | App read-only for certs (U11). |

### 3.6 Score, SOPs, issues, notifications, long tail

| Prototype | Today | Gap | Backend | Note |
|---|---|---|---|---|
| Scorecard: last published grade, 70/20/10 rows, KRAs with met/below, "figures come from group dashboards", report a figure | `/dashboard/kpi` with KRA, competency, initiative, `overall_grade`, `pip` | R | `kpi.get_my_kpi_dashboard` | Mostly done. Check copy: "grades set by HR at period end, not live". |
| SOPs: search, chips incl. "Needs reading", detail with owner, version, your status, Mark as read | `/sop` list + detail, no read tracking | **N + P (Q8)** | new `SOP Acknowledgement` (sop, version, employee, on); `required_for` roles on SOP Document | HR "who read v3.1" report. |
| Issues: chips Pending / All / Payroll and HR / App and IT; detail with timeline, reply, mark resolved | Employee Issue (HR notes, employee read-only) and native Helpdesk (reply thread) | **P (Q3 of compact, still unanswered)** | `helpdesk.*` has reply, options, ticket | One system. Recommendation below. |
| Notifications: log rows with plain copy; Mark all read; "13 check-ins cleared quietly" | `Notifications.vue` | S | PWA Notification producers (`PWANotificationsMixin`); quiet count from accepted remote check-ins | Copy is code here, not a Notification template (section 4). |
| Holidays with "Long weekend" and "Bridge it" | Holidays component on Leave dashboard | R | `get_holidays_for_employee` | |
| Profile: details, contact, payroll documents, scorecard, training, company info, HR contacts | `/profile`, `/hr-contacts` | R | existing | Payroll documents: **out** (payroll stays out of Verifica). |
| More: profile, history, holidays, SOPs, team roster, settings, log out | `/more` | R | existing | Keep Approva and Project Board app links. |
| "Viewing as" role switch | prototype device only | drop | role comes from the server | |
| Headcount request | stub | out | recruitment chain lives in Desk | |

---

## 4. Where the mapping document is wrong for this fork

Each row changes an estimate or prevents a duplicate build.

| # | Mapping says | This fork | Consequence |
|---|---|---|---|
| 1 | ERPNext v15 + hrms v15 | Frappe 16 fork on `nz-glass`; `/hr/roster` page is not present (`hrms/hr/page` has organizational_chart and team_updates only); `/team/roster` in the PWA with `hrms/api/roster.py` is the roster | Do not link to a Desk roster page; extend ours. Shift Schedule, Schedule Assignment and Shift Assignment Tool are present. |
| 2 | Overtime Claim is a gap; build a custom doctype | `OT Request` exists with monthly caps, rate bands, precision work and a reservation index (360 ledger) | Do not build another. The prototype's OT form is a restyle of `OTRequestForm`. |
| 3 | Grade band and PIP threshold need a custom field and a server script | Appraisal already carries `overall_grade`, `employee_band`, `pip`, `grade_scale_html` | Score screen is a reroute. Check the threshold lives in a setting, not code. |
| 4 | SOP + SOP Acknowledgement both custom | `SOP Document` exists | Only the acknowledgement doctype is new. |
| 5 | Issues: Support Issue or HD Ticket | Both `Employee Issue` (HR-confidential fields, HR board) and native Helpdesk (`hrms/api/helpdesk.py`) exist | The decision is which is the one employee-facing system, not what to build. |
| 6 | Geofence: set `checkin_radius` and alert outside it | Shift Location + Shift Location Rule + Remote Checkin Request + Geofence Reject Log; producer-side notification fixes landed 8 Sep (N05, N07, N08) | The "134 notifications" fix is mostly a producer condition, partly done. Remaining: N01–N04, N09. |
| 7 | Notification copy is a Notification template edit, not code | PWA Notification has its own producers in `PWANotificationsMixin` | Copy rewrite is a code slice with tests (U4). |
| 8 | Compensatory Leave Request for replacement days | Custom `Replacement Leave Claim` with hub-granted allocations and an HR-configurable ratio | Keep ours. The prototype's "claim replacement day" maps to it directly. |

Also verify on the live site before estimating (mapping §6 still applies):
ERPNext `Vehicle` installed; `Attendance Request.reason` options; whether
`Travel Request` is enabled; Helpdesk installed on Verifica.

---

## 5. Decisions that block the build

Each one changes what gets built. Recommendation first, so a "yes" is one word.

| # | Decision | Recommendation | Who |
|---|---|---|---|
| Q0 | Look target | **The prototype's flat, still material becomes the spec.** Token names stay, values re-tune to the grid in the surface map §1; the Glass light field, bevel and blur retire. This reverses phase 9 decisions D2/D3 on purpose; recorded as spec addendum §18. | Nabil + P&C |
| Q1 | Tab bar | **Home · Calendar · Requests · Score · More** as prototyped. Approvals as a header icon plus "Needs you", never a tab (it would vary by role and break the fixed-five rule). Doubt on record: Score is a quarterly screen in a daily bar; revisit with four weeks of usage. | Nabil + P&C |
| Q2 | Approve all leave | **No at launch.** Ship behind an HR Settings toggle, default off, only after HR rules on it. Bulk approval without per-request cover context contradicts U8. | HR |
| Q3 | One issue system | **Native Helpdesk** as the employee-facing surface where installed (reply thread, categories Payroll or OT / App bug / Other route to HR or IT). Employee Issue stays for HR-confidential types only if HR insists; otherwise migrate. Open since 7 Sep. | HR + IT |
| Q4 | Leave form policy: which leave types require a document; birthday leave fixed to the date of birth (what if it falls on a rest day); unpaid warning wording; does the balance check block or warn | Document required for Medical, Hospitalisation, Prolonged illness. Birthday: fixed date, moves to the next working day if on a rest day or holiday. Balance check warns only (U9). | P&C |
| Q5 | Expense and travel money: single-line claims; receipt always mandatory; source of "reimbursed with <date> payroll"; advance mandatory above a threshold; does approved travel write Attendance as On Duty; does pending travel show on the team calendar | Single-line at launch (multi-line later). Receipt mandatory. Travel writes On Duty via Attendance Request on approval. Pending travel shows on the team calendar marked pending. | Finance + P&C |
| Q6 | Events source | Frappe `Event` with category "Company" edited by HR. M365 read later if HR keeps the calendar there. One source. | HR |
| Q7 | Roster cover rule for F&B outlets | "At least one opener and one closer per day" as a per-Shift Location setting; days below it flagged, never blocked. | Outlet ops |
| Q8 | SOP acknowledgement and certifications: per-version read tracking with `required_for` roles; HR maintains an Employee Certification table; app read-only | Yes to both; HR owns the data. | HR |
| Q9 | Nudge approver and auto-reminder | Auto reminder at 48 h by scheduler; manual nudge once per 24 h after that. | P&C |
| Q10 | Scope of 2.0 launch | Phases 0–2 (friction + IA) are the launch. Phase 3 domains ship one at a time behind their decision, travel first. | Nabil |

---

## 6. Delivery plan

Order of work, by risk and by what needs no decision:

1. Instruments and the contract, so every later slice is measured.
2. Friction on flows that exist (needs no policy, biggest daily pain).
3. Information architecture (needs Q1, Q2).
4. New domains, one at a time, each behind its decision.
5. Polish gates (Track B) once a served site exists for the gates.

Every slice: one public behaviour named, a red test on HEAD first, an isolated
worker (`executor`, worktree), a fresh `verifier` before integration, a commit
under 400 source lines with its tests, the review hook, no push without word.

### Phase 0 — Contract, mockup, instruments

| # | Slice | Done when |
|---|---|---|
| 0.1 | Record Q1–Q3 in `docs/glass/decisions/` | Three decision files with a signature line. |
| 0.2 | Spec addendum §17: the UX contract (section 2) and the tab bar ruling | Addendum committed; spec §13.1 amended. |
| 0.3 | Mockup: the prototype IS the visual contract (Q0). `mockup-builder` re-renders Home, Calendar + day sheet, Requests hub + New sheet, Leave form, Request detail, Approvals + detail on the grid values of surface map §1, so sign-off is on snapped numbers, not on the prototype's odd ones | Sign-off per screen family. |
| 0.4 | Gates for the **G** rules: copy lint (U4), balance arithmetic lint (U9), API ownership allowlist (U11), fence AST test (U12), resource-states gate at all three containers (U2) | Each gate red on a deliberate breach, green on HEAD. |
| 0.5 | E2E journeys J2 check-in, J3 request, J4 approve run in CI against a served site (THE_PLAN phase 2 items still open) | `critical-paths.spec.js` covers punch, submit, approve-and-stays-approved. |
| 0.6 | Token re-tune to the grid (surface map §1.1–1.4): spacing scale, radii, type roles, tab bar 56, header 56; generated CSS regenerated; both themes re-measured with `app-measure.mjs` | Every token value equals the table; `design/gates` baselines refreshed on purpose. |
| 0.7 | The 22-primitive kit (surface map §1.3): build or retune each once, with its measured height pinned in a node test; the nine `*Item.vue` rows and the filter sheet retire behind `RequestRow`, `StatusPill`, `Chip` | Kit tests green; census gate U14/U15 green on the kit files. |

### Phase 1 — Friction on what exists (no policy needed)

| # | Slice | Prototype ref | Red test |
|---|---|---|---|
| 1.1 | Shared `RequestSummary` block on all six forms: days, balance after, approver, what happens next | every form's `.summary` | node:test per form: block present with the right rows. |
| 1.2 | Done screen after submit, with View request / Done | `s-done` | e2e: submit lands on Done, not on the detail form. |
| 1.3 | Request detail progress timeline from status and the approval log; Rejected doc renders read-only | `s-reqdetail` | node:test: three steps, current step marked. |
| 1.4 | Withdraw sheet with consequence copy ("N days return to your balance") | `sheet-wd` | node:test + python: `withdraw_request` returns the days released. |
| 1.5 | Six states in `FormView` (skeleton, error) and offline banner that disables the punch | work order 9.7a, 9.7b minimum | resource-states gate red on HEAD for FormView. |
| 1.6 | One error presenter: permission and server errors in plain language, no doctype names | work order 9.7c | copy lint red on today's toasts. |
| 1.7 | Check-in card states: punched-pending, strict-block exit into a prefilled correction | `h-state`, GOLIVE "punched, pending" | node:test for each state. |
| 1.8 | Approvals pending state after tap; detail shows balance, cover that day, age | `renderAp`, `openAp` | node:test: row disabled while deciding; cover row rendered. |
| 1.9 | History includes OT, attendance and RL | `RequestPanel:108` stale comment | node:test: nine types in history. |
| 1.10 | Clock-in history grouped by day with missing-punch flag and stats | `s-punches` | node:test: a day with IN and no OUT shows "No clock-out" and offers a correction. |
| 1.11 | Notification copy rewrite in the producers; quiet-clear count in the feed; tap destinations (N09) | `LOG`, `nt-quiet` | python producer tests per event; copy lint. |

### Phase 2 — Information architecture (needs Q1, Q2)

| # | Slice | Prototype ref | Red test |
|---|---|---|---|
| 2.1 | Tab bar Home · Calendar · Requests · Score · More; old routes redirect; deep links, reload and back per tab | `nav.tabs` | e2e: every old URL lands; back stack per tab. |
| 2.2 | Home v2: greeting, check-in card, "Needs you" aggregator (approvals, geofence, issue replies) capped at 3, "Your requests" two rows; QuickLinks removed | `s-home` | node:test on the aggregator; e2e Home shows a pending approval as a row. |
| 2.3 | Requests hub cards and the New request sheet with per-type balances and the Unpaid marker | `s-requests`, `sheet-new` | node:test: six leave tiles with balances from the map. |
| 2.4 | Leave balances screen with ledger breakdown | `s-balances` | python: `get_leave_ledger_breakdown` sums to the allocation balance. |
| 2.5 | Calendar v2: legend, stats, open-request ring, day sheet with the contextual action matrix | `s-attend`, `sheet-day` | node:test: matrix (day state → actions). |
| 2.6 | Claims screen: owed / awaiting payroll / pending / paid, status map | `s-claims` | python: Unpaid maps to Awaiting payroll; trip-linked excluded from owed. |
| 2.7 | Unified approvals queue API and screen: Waiting / Decided, geofence group, in-place decide | `s-approvals` | python: queue lists all six types for a routed approver, none for a stranger; node:test for chips. |
| 2.8 | Team day view by department with counts and the manages-nobody empty state; roster cover flags (Q7) | `s-team`, `s-roster` | node:test: counts; cover flag when no opener. |
| 2.9 | More v2 and Holidays with "Bridge it" prefilling leave | `s-more`, `s-holidays` | e2e: Bridge it opens the leave form with the date. |

### Phase 3 — New domains (each behind its decision; each gets a schema slice reviewed by `migration-checker` first)

| # | Domain | Slices | Decision |
|---|---|---|---|
| 3.1 | Travel: PWA form on Travel Request with costing and advance flag; "Travelling" on own and team calendar; approvals type seven; trip money on Claims; geofence auto-clear when approved travel covers the day | 5 | Q5 |
| 3.2 | SOP acknowledgement: doctype, `required_for` roles, "Needs reading" chip, Mark as read, Home row, HR who-read report | 3 | Q8 |
| 3.3 | Assets: read-only My assets from Asset custodian + movement history; detail; report an issue prefilled; then Asset Request doctype with approve → Asset Movement | 4 | Q3 (assets) |
| 3.4 | Training and certifications: Employee Certification table, daily expiry scheduler, Home "Renew" row, completed training from Training Result, training request | 4 | Q8 |
| 3.5 | Issues unification on Helpdesk: categories, reply timeline, resolve, Home "replied to your issue" row | 3 | Q3 |
| 3.6 | Events carousel from one source | 1 | Q6 |
| 3.7 | Nudge approver and 48 h auto-reminder | 2 | Q9 |
| 3.8 | Offline punch queue (GATE 3 spec) | 2 | none |

### Phase 4 — Polish (Track B, needs a served site with `AUDIT_PW`)

Glass material on every new surface; contrast on the new pills (the prototype's
amber-on-cream and olive-on-white must be measured); 320 px reflow; both themes;
reduced motion; visual baseline refresh; coherence gate carrying the U rules.

### Size

| Phase | Slices | Notes |
|---|---|---|
| 0 | 7 | Gates, the spec addendum, the token re-tune and the kit. 0.6 and 0.7 are product code that every later slice rides on. |
| 1 | 11 | All on existing screens. |
| 2 | 9 | Two of them (2.2, 2.7) carry new aggregation endpoints. |
| 3 | 24 across 8 domains | Each domain is its own mini-plan with a schema slice. |
| 4 | 4 to 6 | Gate-driven. |

Roughly fifty-five commits. Phases 0–2 are the 2.0 launch (Q10).

---

## 7. Verification

- **Per slice:** red test on HEAD first; mapped tests plus importer tests
  green; `verifier` on the diff before integration; the review hook after commit.
- **Per phase:** persona probes with Playwright as employee, named approver
  without reports, HR without the Employee role, and a cross-company user (the
  recipe in memory from the 7 Sep notification probes). Every screen family in
  both themes at 320, 390, 768 and 1440.
- **Contract gates** (section 2, **G** rows) are required checks; a breach
  blocks the commit.
- **Release:** GATE checklist, `scripts/smoke.sh`, the approval e2e against the
  live URL after Nabil deploys on Frappe Cloud.

---

## 8. Risks

| Risk | Where it bites | Guard |
|---|---|---|
| Leave against a rostered shift: half-day hours differ by shift (mapping §5.1) | 2.5 day sheet, leave form | Test: half-day leave on a closing shift. Server computes days (U9). |
| Auto-attendance and an approved correction for the same day fight (mapping §5.2) | 1.7, 3.1 On Duty write | Precedence rule written before 3.1; existing ATT-PROVISIONAL guard. |
| Two sources of truth for assets and certifications (mapping §5.3) | 3.3, 3.4 | U11 gate; app reads only. |
| Shift overlap error illegible (mapping §5.4) | 2.8 roster | Error presenter (1.6) covers it; test with an overlapping insert. |
| Tab change breaks Ionic navigation stacks | 2.1 | e2e per tab: deep link, reload, back. |
| Verifica cutover in flight; schema changes during the freeze | all of phase 3 | No schema slice without the user's word for that exact change; `migration-checker` before deploy. |
| Multi-company leak on a new aggregator | 2.2, 2.7 | U12 AST gate; cross-company persona probe. |
| The compact proposal and this plan drift apart | Q1 | Fold the compact proposal into this document once Q1 is signed; retire it. |

---

## 9. Out of scope

Headcount requests (recruitment stays in Desk). Payroll documents and pay slips
(payroll stays out of Verifica). Desk changes beyond the patches a slice needs.
M365 writes. A Vehicle screen if ERPNext Vehicle is not installed on the site.
The frappe-ui upgrade (its own project).

---

## 10. Pipeline summary

- **Requirements:** this document plus the prototype and mapping in
  `Nadi PWA UI UX 2.0/`. Decisions Q1–Q10 recorded in `docs/glass/decisions/`.
- **Planning agents:** per phase 3 domain, `scope-analyzer` → `impl-designer`
  → `test-planner`; `arch-reviewer` on 2.7 (queue API) and each schema slice;
  `security-checker` on every new whitelisted endpoint; `migration-checker`
  before any schema slice deploys.
- **Workspace:** branch `nz-glass`, worktree `/home/nabil/nz-version-16`;
  workers in their own worktrees; no shared files between concurrent workers.
- **Mockup:** phase 0.3, `mockup-builder`, signed off per screen family before
  its phase 2 slice starts.
- **TDD:** red test on HEAD per slice (node:test for components and data,
  bench-free python for API, Playwright for journeys); vertical slices, one
  concern per commit.
- **Auto-commit:** after mapped and importer tests pass; conventional message;
  the family ledger for every `fix:`.
- **Auto-review:** the post-commit hook dispatches `frappe-reviewer`,
  `design-reviewer` and `cross-app-impact` as it selects; Critical fixed and
  re-committed.
- **Auto-deploy:** Nabil pushes and deploys on Frappe Cloud; every server
  change lands through a patch or hook; `scripts/smoke.sh` and the live
  approval e2e after each deploy.

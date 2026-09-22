# Nadi 2.0 — the plan of record

16 September 2026. Branch `nz-glass`. This document replaces the 2.0 doc chain
(see §8). Every number below was read out of the tree today.

## 1. What 2.0 is, and is not

2.0 makes the shipped Nadi PWA **read like a product for staff instead of a
database front end**, on phones and on desktop. The design system we already
ship — "Glass" — stays. The work is the words the user reads, the structure of
each screen, the desktop layout, and the four journeys in priority order. It is
**not** a re-skin, not a token change, not Desk, not backend, not doctypes, not
schema, not new features.

## 2. Decisions locked today

1. **Glass wins.** Brand `#C8FF00`, the Inter Tight display stack, the radius
   ladder (panel 20 / action 19 / card 17 / banner 16 / tile 15 / input 14 /
   well 9 / pill 6 / tabbar 22) and the spacing scale (gutter 15px, stack
   9/13/16, pad-panel `14px 13px`, pad-row `11.5px 15px`, pad-action `17px 18px`)
   stay exactly as `design/tokens.json` has them. Token churn is out of scope.
2. **The prototype is layout and language only.** `Nadi PWA UI UX 2.0/nadi-prototype.html`
   (36 screens, 5 sheets) gives screen structure, information architecture and
   plain wording. Its colours and fonts are **not** adopted — it ships a system
   font stack and a different lime, neither of which enters the app.
3. **Glass blur on chrome only** — tab bar, side nav, header, sheets + scrim,
   toast, floating CTA, check-in action layer; content surfaces opaque. The
   standing 10 Sep Amendment A ruling (U16), carried forward, not re-opened.
4. **Desktop is a two-column app shell**, reusing what is built: `SideNav.vue`
   replaces the bottom tab bar at `min-width: 1024px` (`TabbedView.vue` /
   `FormShell.vue` render both; the bar is `lg:hidden`), content column
   `--g-content-column-lg: 720px` (**provisional**), modals become centred 480px
   dialogs at lg, balance grid 2-up on mobile → 4-up at lg.
5. **Priority order:** (1) Home/dashboard, (2) Attendance & OT claims,
   (3) Requests, (4) Approvals + Helpdesk.
6. **Brand lime A/B is OPEN**, not decided — see §3.
7. **Employee Advance stays hidden.** No route, tile, label or link. Verified:
   no PWA route exists and `hrms/api/__init__.py:1535` records the omission as
   deliberate. Standing ruling.
8. **Scope is the PWA** at phone and desktop widths. Nothing else.

## 3. Open — ANSWERED 22 Sep 2026

All five were put to the owner after the pre-2.0 programme shipped, and all
five came back in one line each. Recorded verbatim, because "as planned" only
means something if the plan it points at is named.

| # | Question | Answer |
|---|---|---|
| O1 | Brand lime: shipped `#C8FF00` vs prototype `#c4ee15` | **SHIPPED.** `#C8FF00` stays. The prototype's lime is not adopted, the mockup's A/B switch is settled, and no token moves — so the 114 visual baselines stay valid and §7's "token values are not in scope" holds without an exception. |
| O2 | Desktop content column: 720px, provisional | **ACCEPTED.** `--g-content-column-lg: 720px` is the signed-off value, not a placeholder. D.1 no longer waits on anything. |
| O3 | Do the three light-field blobs stay? | **THEY STAY.** Amendment A Q0a proposed retiring `GLightField`; declined. `GPage.vue` keeps rendering them and the `field.*` tokens keep shipping. |
| O4 | Tab bar set | **AS PLANNED: Home · Calendar · Requests · Score · More.** This replaces the five in `data/navItems.js` (Home · Attendance · Leaves · Expenses · More). Old routes keep working through redirects — five fixed tabs, because Ionic stacks them. |
| O5 | UX_PLAN Q2–Q10 | **AS PLANNED.** Each takes the recommendation already written in `NADI_2.0_UX_PLAN.md` against its row; none is re-opened here. Where that document offers a choice rather than a recommendation, it is a slice-time question, not a plan-level one. |

O4 is the one that reorders the work: the tab set decides what Home is for, so
slice 1.3 now depends on a new slice 0.1 (the tabs themselves) rather than the
other way round. The priority order in §6 is amended accordingly.

## 4. Evidence: what the app actually is

Not a stock Frappe/Ionic app. Verified today:

- **151 `.vue` files** under `frontend/src`; a custom library of **42 Glass
  components** in `frontend/src/components/glass/`. Most reused: GPage 27,
  GEmptyState 23, GSkeleton 18, GButton 17, GStatusChip 14, GModal 14.
- **Ionic is structural only.** `<ion-list>` / `<ion-item>`: **zero**. What is
  used: IonContent 23, IonModal 10, IonPage 6, IonRefresher 1, plus one stray
  `<ion-toolbar>`.
- **frappe-ui is mostly a data layer**: createResource 50, FeatherIcon 27,
  toast 20, createListResource 6, createDocumentResource 4. Visual leftovers are
  few: Autocomplete 6, Button 4, Input 3, LoadingIndicator 3, Badge 2,
  ErrorMessage 2, and one each of Switch, Popover, FormControl, TextEditor,
  DatePicker, DateTimePicker, Dialog, Dropdown.
- **Token pipeline**: `design/tokens.json` → `design/build-tokens.mjs` →
  `frontend/src/theme/glass.variables.css` + `glass.tailwind.cjs`. Gates in
  `design/gates/*.mjs` (lint, usage, contrast, surfaces, a11y, visual), run by
  `yarn gates`.
- **Visual baselines: 114 PNGs** = 38 screens × `390-dark`, `390-light`,
  `1440-dark` (`design/baselines/README.md`) — masked, so never cite them as
  screenshots of the app.
- **Routes**: `frontend/src/router/index.js` plus per-domain files: attendance,
  claims, helpdesk, helpdeskHub, issues, leaves, ot, sop.

## 5. The residue ledger — Frappe leaking to staff

This is the heart of 2.0. Every line verified today.

| file:line | What the user sees | New wording |
|---|---|---|
| `components/FormView.vue:335` `__('Delete {0}', [__(props.doctype)])` | "Delete Employee Checkin" | "Delete this clock-in record" |
| `FormView.vue:354` `__("Permanently submit {0}", …)` | "Permanently submit OT Request" | "Send this overtime request?" |
| `FormView.vue:376` `__("Permanently cancel {0}", …)` | "Permanently cancel Leave Application" | "Cancel this leave request?" |
| `FormView.vue:736` `__("{0} deleted successfully!", …)` | "Attendance Request deleted successfully!" | "Your attendance fix was deleted." |
| Doctype props feeding the four above: `views/attendance/EmployeeCheckinList.vue:4` "Employee Checkin", `AttendanceRequestForm.vue:6` "Attendance Request", `ShiftAssignmentForm.vue:6` "Shift Assignment", `ShiftRequestForm.vue:6` "Shift Request", `ot/OTRequestForm.vue:6` "OT Request", `ot/ReplacementLeaveClaimForm.vue:6` "Replacement Leave Claim", `leave/Form.vue:6` "Leave Application", `expense_claim/Form.vue:6` "Expense Claim", `issues/IssueForm.vue:6` "Employee Issue" | The database name of the record, in every confirm and toast | One plain label per screen, passed in beside the doctype |
| `components/ShiftAssignmentItem.vue:44` `props.doc.docstatus ? "Submitted" : "Draft"`, rendered with `:label="status"` (untranslated) | Chip reads "Draft" / "Submitted" | "Not sent yet" / "Sent" |
| `components/ShiftRequestItem.vue:52` `props.doc.docstatus ? props.doc.status : "Open"`, also `:label="status"` (untranslated) | Raw English state on the chip, bypassing `__()` | Translate + plain words: "Open" → "Waiting for a decision" |
| `components/AttendanceRequestItem.vue:48` fallback `"Draft"` (label *is* translated) | "Draft" | "Not sent yet" |
| `components/ExpenseClaimItem.vue:56` composite `["Draft","Unpaid","Submitted"]` | "Approved & Unpaid" | "Approved — payment on the way" |
| `views/attendance/ShiftRequestList.vue:36` `STATUS_FILTER_OPTIONS = ["Draft","Approved","Rejected"]` | Filter chips read "Draft" | "Not sent yet" / "Approved" / "Rejected" |
| `views/expense_claim/Form.vue:184` and `views/leave/Form.vue:193` — `excludeFields` containing `"naming_series"` | Nothing today, because each screen blacklists internals by hand. A generic doctype-field renderer leaks the next internal field the moment one is added. | Invert it: an allowlist of fields per screen, so nothing new can leak |

**Minor / no action.** `HD Ticket` appears only in a comment
(`glass/GStatusChip.vue:62`) and one upload call (`helpdesk/TicketNew.vue:209`).
`HR-EMP-…` IDs appear only in the dev-only `views/DesignSpecimen.vue:507-508`.
One bare `<ion-toolbar>` sits in `components/FilePreviewModal.vue:3` — tidy it
when that modal is next touched.

## 6. Work slices, in priority order

Vertical slices. Each ships alone, carries its own tests, stays under the
**400 changed source line** budget, and is one commit.

| # | GOAL (one line) | DONE WHEN | Files |
|---|---|---|---|
| 1.1 | Every confirm and toast in the form shell names the thing, not the doctype. | No user-visible string contains a doctype name; each form passes its own plain label. | `components/FormView.vue`, the nine `*Form.vue` / `*List.vue` call sites, new unit test |
| 1.2 | Status chips speak plain English and always go through `__()`. | No `:label="status"` without translation; "Draft"/"Submitted" gone from the UI. | `ShiftAssignmentItem.vue`, `ShiftRequestItem.vue`, `AttendanceRequestItem.vue`, `ExpenseClaimItem.vue`, `views/attendance/ShiftRequestList.vue` |
| 1.3 | Home reads like the prototype's Home: check-in, "needs you", then your recent requests. | Home matches the agreed structure; scroll budget at 390×844 not worse than today. | `views/Home.vue`, Home child components |
| 2.1 | Attendance dashboard and clock-in history follow the prototype's structure and wording. | Both screens re-laid out; baselines re-shot deliberately. | `views/attendance/Dashboard.vue`, `EmployeeCheckinList.vue` |
| 2.2 | OT claims read as money owed, not as documents. | OT list and form use plain labels; no doctype words. | `views/ot/*` |
| 3.1 | Requests screens use an allowlist of fields, not a blacklist. | `excludeFields` gone; adding a backend field cannot leak. | `views/expense_claim/Form.vue`, `views/leave/Form.vue`, `components/FormView.vue` |
| 4.1 | Approvals and the Helpdesk hub follow the prototype's structure. | Both screens re-laid out; approver journey unchanged. | `views/RemoteApprovals.vue`, `views/helpdesk/*` |
| D.1 | Desktop shell signed off at the chosen column width. | O2 answered; the token matches the answer; 1440 baselines re-shot. | `theme/glass.css`, `components/SideNav.vue` |

## 7. Explicitly NOT in scope

Token values · a new colour or type system · Desk · backend, API, doctype,
schema or permission change · payroll (stays out of Verifica) · Script Reports
(deferred) · new domains (travel, assets, training, events) · Announcements
(committed launch scope, still unbuilt — it is a feature, not a 2.0 slice) ·
Employee Advance · CI or deploy changes inside a UI slice.

## 8. Which old docs still count

All nine live in `docs/glass/plan/`.

| Doc | Verdict |
|---|---|
| `NADI_2.0_UX_PLAN` | **PARTIALLY VALID** — Q0 ("retire Glass") is dead; Amendment A reversed it and today confirms Glass. The U1–U15 contract rules and Q1–Q10 survive as open questions. |
| `NADI_2.0_AMENDMENT_A_LIQUID_GLASS` | **PARTIALLY VALID** — its chrome-only ruling (U16) and the reachability/readability rules (U17/U18) are carried into this doc. Its Q0a blob question is still unruled (O3). |
| `NADI_2.0_SURFACE_MAP` | **PARTIALLY VALID** — the measurements survive and are still the scroll-budget reference. Its "go flat / retire blur" recommendation does not. |
| `NADI_2.0_DELIVERY_PLAN_2026-09-13` | **SUPERSEDED** by §6 here. Its five-journey framing survives as the priority order. |
| `NADI_2.0_EXECUTION_WAVES` | **PARTIALLY VALID** — the regression controls and the one-packet-at-a-time rule survive; all day-estimates are dead (pace is by verified milestone). |
| `NADI_2.0_W0_BASELINE` | **STILL VALID** as a dated evidence record. Its numbers are a snapshot, not current state. |
| `NADI_2.0_API_CONNECTIONS` | **STILL VALID** as a seed RPC inventory; not a coverage claim. |
| `NADI_2.0_ANNOUNCEMENTS` | **STILL VALID** — committed launch scope, unbuilt, outside 2.0's slices. |
| `NADI_COMPACT_UX_PROPOSAL` | **SUPERSEDED** in full. |

**Standing constraints carried forward.** Pace by verified milestones, never by
day-estimates. Script Reports deferred. Payroll stays out of Verifica. No
schema, permission or CI change inside a UI slice. `scripts/smoke.sh` **mutates**
— it runs `bench migrate` (line 38) — so it is never a read-only check.

## 9. How each slice is proved

1. **Red first** — a failing unit test on HEAD (`cd frontend && yarn test`).
2. **Gates** — `cd frontend && yarn gates` (lint, usage, contrast, surfaces,
   a11y, visual). Contrast is enforcing; it exits non-zero.
3. **Baselines** — a slice that changes pixels re-shoots the 114 PNGs on purpose
   (`node design/gates/visual.mjs --update-baseline`) and the diff is reviewed
   screen by screen. Never a blind re-baseline.
4. **Scroll and reach** — `cd frontend && node e2e/app-measure.mjs` at 390×844,
   compared with the prototype measurement.
5. **Unmasked evidence for the owner** — `docs/glass/audit/screens/`.

No push, no deploy, no schema or policy change without the owner's word for
that exact change.

# Addendum — audit re-run against `Nastyworldwide-Dev/hrms@nz-version-16`

**Supersedes sections 1, 2.5 and 5 of `HR_Glass_Implementation_Research_v1.md`.** That audit was run against `frappe/hrms@develop`, which turns out to be the wrong baseline. Everything in §2.1 (contrast), §2.2–2.4 (token defects), §2.6 (disabled/pending) and §4.1 (backdrop-root) is unchanged and still applies.

---

## 1. Your three answers

| Question | Answer |
|---|---|
| Architecture route | **Fork + token refactor** — confirmed by the branch itself; you are already three-quarters through one of these |
| Spec authority | **Amendable** → I'll produce v1.1 |
| Overtime / KPI / Issues in scope? | **All three already exist and are built.** The scope contradiction in §2.5 of the first document dissolves |

---

## 2. Overtime, KPI, Issues — built, with backends

| Area | Doctypes | API | Screens |
|---|---|---|---|
| **Overtime** | `ot_request`, `overtime_slip`, `overtime_type`, `overtime_details`, `overtime_salary_component`, `attendance_overtime_band`, `shift_overtime_rate` | — | `ot/OTRequestForm`, `ot/OTRequestList`, `ot/ReplacementLeave`, `ot/ReplacementLeaveClaimForm` |
| **KPI** | `kpi` | `api/kpi.py` (+ tests) | `kpi/Dashboard` |
| **Issues** | `employee_issue` | — | `issues/HRIssueBoard`, `issues/IssueForm`, `issues/IssueList`, `issues/IssuesTab` |

Also present and **not covered by the Glass spec at all**: SOP (`sop_document`, `api/sop.py`, 3 views), Team (`api/team.py`, `TeamDashboard`), Remote approvals (`api/approval.py`, `RemoteApprovals`), Remote check-in (`remote_checkin_request`, `api/remote_checkin.py`), Geofencing (`api/geofence.py`, `geofence_reject_log`), HR Contacts, Replacement Leave Claim, Employee Promotion.

**Consequence:** Glass is a re-skin of a working, feature-complete app. The risk is not over-reach — it's that the spec covers roughly a third of what exists and the rest gets improvised.

---

## 3. The correction that matters most: there is already a design system

The first audit said "no token layer, 341 hardcoded utilities, zero dark mode." That is true of upstream. It is **not** true of your branch. You already built one — `Modernist`.

| Layer | What exists on `nz-version-16` |
|---|---|
| Tokens | `src/theme/modernist.css` — 351 lines. Hex palette + `--m-*` RGB triplets, warm neutral ramp, teal accent ramp, spacing, radius, motion, shadow. Light in `:root`, dark in `:root.dark` |
| Tailwind bridge | `darkMode: "class"`, semantic colours `ink-100…900`, `accent-100…900`, `ground`, `surface`, `inkbase`, `divider`, all as `rgb(var(--m-*) / <alpha-value>)` |
| Primitives | 14 `.m-*` classes — `m-btn-primary`, `m-chip` (+3 variants), `m-row`, `m-kicker`, `m-rule`, `m-bar`, `m-statnum`, `m-poster`, `m-avatar-sq` — ~150 usages |
| Theme switch | `data/theme.js` — light / dark / system, persisted to `localStorage`, `.dark` on `<html>`, **View Transitions circular reveal**, and `<meta name="theme-color">` swapped per theme |
| Ionic theming | `BottomTabs.vue` already themes `ion-tab-bar` / `ion-tab-button` through shadow-DOM CSS vars, with `contain: content` and `height: auto` — with a comment explaining why |

**Revised debt numbers (fork, not upstream):**

| Metric | Upstream `develop` | Your branch |
|---|---|---|
| `.vue` files | 79 | **103** |
| Hardcoded colour utilities | 341 | **98** |
| `dark:` variants | 0 | 5 |
| Arbitrary values `[...]` | — | **303** |
| Raw hex in `.vue` | — | ~25 |

This is genuinely good news. **The mechanism the Glass spec asks for already exists and is proven in production.** §13's "tokens as CSS custom properties switched by an attribute on the root, no duplicated stylesheets, no theme prop threaded through components" — done. The remaining questions are about values and primitives, not infrastructure.

Three items from spec §13 are already solved: theme-color meta, persisted theme with system default, Ionic shadow-DOM theming. One is **not**, and still needs fixing: the viewport meta is still `viewport-fit=cover maximum-scale=1.0` — space-separated where it must be comma-separated. That directive is what makes `env(safe-area-inset-*)` non-zero on iOS, and you have `standalone:pb-safe-bottom` logic depending on it.

---

## 4. The new central risk: Modernist and Glass are opposite systems

This is not a palette swap. The two systems disagree on nearly every axis.

| Axis | Modernist (built) | Glass (spec) | Conflict |
|---|---|---|---|
| Radius | **0 everywhere** — `tailwind.config.js` zeroes `borderRadius` for `sm`/`DEFAULT`/`md`/`lg`/`xl`/`2xl`/`3xl` | 9 / 14 / 16 / 17 / 19 / 20 / 22 | **Severe.** Restoring the scale silently rounds every element that currently relies on `rounded-*` being 0 |
| Surface | Flat, opaque, `--color-surface` | Translucent + `backdrop-filter` + light field | Full rewrite of every panel |
| Borders | 2px dividers (`border-t-2`, `border-l-[3px]`) | 1px rims + inset highlight/shadow pair | Every divider |
| Type | Archivo 400/600/800, **Google Fonts CDN** | Inter + Inter Tight, `-apple-system` first, self-hosted | Font swap + hosting change |
| Accent | Teal `#0B313A` / mint `#A1EEC9` | Chartreuse `#C8FF00` | Full ramp replacement |
| Ground | `#f3f2f2` / `#191817` (warm) | `#EDEFF3` / `#07070A` (cool) | Full ramp replacement |
| Elevation | 3 shadows via `color-mix` | `--lift` + two inset rims | Different model |
| Motion | press 120 / glide 220 | press 120 / push 280 / sheet 340 / theme 400 | Extendable |
| Ramp shape | 9-step numeric (`ink-100…900`) | 3-step semantic (`--ink`, `--ink2`, `--ink3`) | **Naming model conflict** — see below |
| Viewport | Mobile + **desktop side nav at `lg:`** | "Mobile only, desktop out of scope" | Spec scope error |

Two of these need a decision before anything is written:

**4.1 Ramp shape.** Modernist uses a 9-step numeric ramp with Tailwind opacity modifiers (`bg-inkbase/[0.04]`). Glass uses 3 semantic ink levels plus pre-composited alpha surfaces. You cannot run both without the system fragmenting. Recommendation: keep Modernist's *mechanism* (RGB triplets + `<alpha-value>`) and replace the *vocabulary* with Glass's semantic names, adding the glass-specific surfaces (`--glass-fill`, `--glass-rim`, `--rim-hi`, `--rim-lo`, `--sheen`, `--hair`, `--lift`) as their own group.

**4.2 The 303 arbitrary values.** `text-[8.5px]`, `h-[19px]`, `border-l-[3px]`, `tracking-[0.08em]` hardcode Modernist metrics at call sites, across 103 files. They are invisible to any token swap. These are the single biggest source of drift in the migration, and they need a sweep — either promoted into the Tailwind theme as named scale entries, or absorbed into `.m-*` primitives.

**4.3 Palette is duplicated three ways**, and your own comment in `modernist.css` says so: *"the same hex values are duplicated in tailwind.config.js and variables.css — any palette change MUST be applied to all three files."* Manual 3-way sync is exactly the discipline failure mode this project is trying to avoid. For Glass, generate all three from one `tokens.json`. This is a small build script and it removes an entire class of drift permanently.

---

## 5. Two IA conflicts to settle

1. **Tab bar count.** `TAB_ITEMS` has **8** entries — Home, Attend, Leaves, Expenses, My KPI, Issues, SOPs, More. Glass §8.7 says *five items max, never scrolls*. Decide the five and what falls under More.
2. **Desktop.** `SideNav.vue` exists (72px collapsed / 216px expanded, `lg:` breakpoint, `lg:hidden` on the tab bar). Glass §1 declares desktop out of scope. Either Glass covers `lg:` in this phase or the app ships two visual identities on one codebase.

---

## 6. Revised component inventory gap

The gap is wider than the first audit found, because the fork has more surface. Beyond the 30 rows in §3 of the first document, add:

| Component | File | Why it matters |
|---|---|---|
| Side nav | `SideNav.vue` | Desktop identity |
| Approvals banner | `PendingApprovalsBanner.vue` | Manager path |
| Late checkout dialog | `LateCheckoutDialog.vue` | Ties to spec §9.3 |
| Remote check-in dialog | `RemoteCheckinDialog.vue` | Geofence flow |
| Strict rejection dialog | `StrictRejectionDialog.vue` | Geofence flow |
| Push notification prompt | `PushNotificationPrompt.vue` | First-run |
| PDF inline viewer | `PdfInlineViewer.vue` | Payslips |
| Resource error | `ResourceError.vue` | Maps to spec §9.3 |
| Contact card / info sheet | `ContactCard.vue`, `ContactInfoSheet.vue` | HR Contacts |
| Replacement leave card | `ReplacementLeaveCard.vue` | OT flow |
| OT request item | `OTRequestItem.vue` | OT flow |
| Issue board | `issues/HRIssueBoard.vue` | Column/board layout — no spec analogue |
| SOP form sheet | `sop/SopFormSheet.vue` | Sheet pattern |
| Form shell | `views/FormShell.vue` | Shared form chrome — the highest-leverage single file |

---

## 7. Revised plan

Because the branch already has the architecture, the sequencing compresses:

| Phase | Work | Note |
|---|---|---|
| **0. Spec v1.1** | Fix contrast failures, tokenise brand constants, resolve pending-vs-disabled, add glass-stop rules, correct the mobile-only scope, settle tab count, extend inventory to the fork's real surface | I produce this next |
| **1. Token swap** | `tokens.json` → generates `glass.css` + `tailwind.config` colours + `variables.css`. Retire the 3-way manual sync. Restore the radius scale deliberately | Highest-risk step: the `borderRadius: 0` reversal |
| **2. Primitives** | `.m-*` → `.g-*`, expanded from 14 to ~30, plus the glass recipe as one class. A `/design` specimen route in-app, both themes | The coherence gate |
| **3. Arbitrary-value sweep** | 303 `[...]` values across 103 files, promoted or absorbed | Mechanical, highly promptable, needs a CI gate afterwards |
| **4. Shell + light field** | Per-page light field (backdrop-root rule from §4.1 of the first document), header, tab bar, sheets | Where perf is won or lost |
| **5. Screen migration** | 41 views in dependency order | One prompt per screen against its component contract |
| **6. Desktop** | `lg:` side nav under Glass — if in scope | Depends on §5.2 |

---

## 8. What I need to write v1.1

1. **`HR_FRAPPE_Glass_Light_and_Dark.html`** — the paired mockup. The spec says the mockup governs where they disagree, so I can't resolve conflicts without it. This is the blocker.
2. Decisions on: tab-bar five, desktop in/out, type-size floor (7.5/8.5px as drawn or raised), focus-ring treatment, in-flight state affordance.
3. Whether `docs/discovery/hrms-system-baseline.md` and `.claude/plans/current-plan.md` are current — if so I'll align v1.1 to their vocabulary rather than inventing a parallel one.

---

*Audited against `Nastyworldwide-Dev/hrms@nz-version-16`. Contrast figures from the first document are unaffected and still stand.*

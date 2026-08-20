# HR Frappe · Glass — Build Plan v1

**The single document to work from.** Everything else is reference material, indexed below.
**Target:** `Nastyworldwide-Dev/hrms@nz-version-16` → new branch `nz-glass`
**Date:** 20 August 2026

---

## 0. Where everything is

Seven documents, produced in this order. Only two are live authorities; the rest are the reasoning behind them.

| # | Document | Status | Use it for |
|---|---|---|---|
| 1 | `HR_Frappe_Glass_Spec_v1.1.md` | **AUTHORITY** | The build spec. Tokens, components, states, screens, a11y, budget |
| 2 | `HR_FRAPPE_Glass_Light_and_Dark_2.html` | **AUTHORITY** | The mockup. Governs values, except the 7 exceptions in spec §14.4 |
| 3 | `Mockup_Spec_Reconciliation.md` | Reference | Why v1.1 differs from v1.0. Read if a value looks wrong |
| 4 | `Modernist_to_Glass_Reuse_Map.md` | Reference | What to reuse, reskin, replace, per file |
| 5 | `External_Materials_Survey_Glass.md` | Reference | Library decisions and the frappe-ui upgrade case |
| 6 | `Liquid_Glass_Direction_Note.md` | Reference | Design rationale for P&C; the fidelity ceiling |
| 7 | `HR_Glass_Implementation_Research_v1.md` + `HR_Glass_Research_Addendum_nz-version-16.md` | Superseded | Original audit. The addendum corrects the baseline |

`HR_FRAPPE_Glass_Implementation_Spec__1_.html` (v1.0) is **retired**. Do not build from it.

---

## 1. The gate — nothing starts until these clear

### 1.1 Six decisions

| # | Decision | Owner | Blocks |
|---|---|---|---|
| 1 | Desktop `lg:` in scope? | You | Every component contract |
| 2 | Tab bar five — confirm `HOME · ATTEND · LEAVE · PAY · MORE` | P&C + you | Information architecture, shell |
| 3 | Accept iOS focus-zoom, or raise inputs to 16px | You | Input component |
| 4 | Name the lowest-spec handset in the fleet | You | Performance budget is meaningless without it |
| 5 | Type floor 10px — sign-off on the change from the mockup | **P&C** | Badge, field label, tab label, micro label, mono |
| 6 | Chartreuse confirmed as the corporate palette for HR | **P&C / brand owner** | The whole token set |

Decisions 5 and 6 are the only two that need P&C. Package them as one short memo with a before/after image rather than sending them the spec.

### 1.2 One spike — do this first

**Spike: `frappe-ui` 0.1.105 → 0.1.278 on a throwaway branch.** One day. Count what breaks.

The result reshapes the plan: 0.1.278 already has `data-theme` dark mode, a semantic CSS-variable token system, reka-ui underneath, and 56 components including `CircularProgressBar`, `DatePicker`, `Calendar`, `Combobox` and `Alert` — which are four of the gaps in the spec's inventory. If it lands cleanly, Phase 2 shrinks by roughly a third. If it doesn't, you build those four by hand and defer the upgrade.

Do not start Phase 1 before this answer exists.

---

## 2. Phase map

```
GATE ──► P1 Foundation ──► P2 Primitives ──┬──► P4 Shell ──► P5 Screens ──► P6 Desktop*
                            │              │
                            └──► P3 Sweep ─┘
                                                         P7 Defects (parallel, any time)
```

| Phase | What | Gate to exit |
|---|---|---|
| **P1** | Tokens, theme switch, light-field structure, CI gates | Contrast matrix green both themes; lint passing |
| **P2** | 28 primitives + `/design` specimen route | Every component, every state, both themes, visual baseline captured |
| **P3** | 303 arbitrary-value sweep across 103 files | Zero `[...]` values outside the theme layer |
| **P4** | Page shell, header, tab bar, sheets, safe area | 60fps on the named handset; ≤6 glass surfaces |
| **P5** | 41 views migrated | Per-screen sign-off checklist (spec §18) |
| **P6** | Desktop `lg:` — only if Decision 1 says yes | — |
| **P7** | Duplicate-punch guard, night-shift check-in state | Reproduced then fixed with evidence |

P1 and P2 are where coherence is won or lost, and they are the ones most likely to get compressed under schedule pressure. Resist that specifically.

---

## 3. The prompt sequence

~45 prompts. Each is one commit. Each names its input document and its exit condition.

### Phase 1 — Foundation (6 prompts)

| # | Prompt | Input | Output |
|---|---|---|---|
| 1.1 | Author `tokens.json` from spec §2 — 15 themed, 9 constants, 4 semantic pairs, spacing, radius, type, motion | Spec §2, §4, §5, §8 | `design/tokens.json` |
| 1.2 | Build the Style Dictionary pipeline → `glass.css`, Tailwind theme colours, `theme/variables.css` | 1.1 | Generated files + build script. **Retires the 3-way manual sync** |
| 1.3 | Restore the `borderRadius` scale in `tailwind.config.js` and audit what it silently rounds | Spec §5 | Diff report of every element affected |
| 1.4 | Retarget the theme store to `data-theme` on `<html>`; keep the View Transitions reveal and the `theme-color` swap; add reduce-transparency mode | Spec §6.2, §16.1 | `data/theme.js` updated |
| 1.5 | Self-host Inter, Inter Tight, JetBrains Mono via fontsource; remove the Archivo CDN link | Spec §4.1 | `index.html`, font imports |
| 1.6 | CI gates: no-hex lint, no-arbitrary-value lint, contrast test over spec §14.2, axe, Playwright scaffold | Spec §16.5 | `.github/workflows`, test files |

**Exit:** contrast matrix green, lint red on any violation, theme switches with no layout shift.

### Phase 2 — Primitives (28 prompts + 2)

One prompt per component. Each carries: tokens consumed, all applicable states, a11y role and announced string, props API, specimen entry.

Order matters — build in dependency order so later components compose earlier ones:

**2.0** — Scaffold the `/design` specimen route first, empty. Every subsequent prompt appends to it.

**Tier A, no dependencies (8):** glass surface recipe · primary action · ghost action · badge · workflow status chip · empty state · skeleton · banner

**Tier B, composes Tier A (10):** list row · input · textarea · balance card · stat tile · issue card · note panel · logo well · progress ring · clock

**Tier C, composes A+B (10):** calendar · map panel · selfie panel · score panel · KRA panel · goals panel · app header · modal/sheet · action sheet · toast

**2.29** — Reconcile against the mockup at 1× and fix drift.

**Notes for specific prompts:**
- **Primary action** — include the `pending` state (spec §11.4). Do **not** implement the shimmer sweep (spec §7)
- **Modal** — retain the `CustomIonModal` focus-trap workaround verbatim; reskin via CSS vars only
- **Balance card** — keep `.m-bar-band`, the hatched pro-rated tail. The spec has no equivalent and it's better than what would replace it
- **Calendar** — no opacity multipliers; rest days use `--ink3`, day numbers `--ink-muted`
- **Avatar** — delete `.m-avatar-sq`; the rounding comes back

**Exit:** all 28 render in `/design` in both themes, every state; Playwright baseline captured.

### Phase 3 — Sweep (4 prompts)

| # | Prompt | Scope |
|---|---|---|
| 3.1 | Inventory all 303 arbitrary Tailwind values across 103 files; classify promote / absorb / delete | Report only, no edits |
| 3.2 | Promote the keepers into the Tailwind theme as named scale entries | `tailwind.config.js` |
| 3.3 | Rewrite call sites to named utilities | 103 files, mechanical |
| 3.4 | Retire the `.m-*` primitives superseded by Phase 2 | `theme/modernist.css` → `theme/glass.css` |

**Exit:** the no-arbitrary-value lint from 1.6 passes with zero exceptions.

### Phase 4 — Shell (5 prompts)

| # | Prompt | Note |
|---|---|---|
| 4.1 | Per-page light field — **inside each page's stacking context** | Spec §3.2. Everything visual depends on this being right |
| 4.2 | `BaseLayout` rebuild: page scaffold, header, safe area | Replaces, not reskins |
| 4.3 | Tab bar → floating pill, five fixed destinations, Ionic host restyle | Decision 2 |
| 4.4 | Fix the viewport meta separator; remove `user-scalable=no` | Spec §13.2 — currently breaks `env(safe-area-inset-*)` |
| 4.5 | Glass-surface counter wired into CI | Spec §15 |

**Exit:** 60fps sustained scrolling on the named handset; no screen over 6 surfaces; safe area verified on a real iPhone.

### Phase 5 — Screens (~41 prompts, batched)

One prompt per view, each pointed at its spec §12 anatomy row. Batch in this order:

1. **Mockup screens first (8)** — Sign in, Home, Check in, Leave, Attendance, Overtime, KPI, Issues. These have drawn references
2. **High-reach shared surfaces (3)** — `ResourceError` (21 usages), `EmptyState` (15), `ListView` (7). Disproportionate visible payoff
3. **Remaining employee views (~18)** — Expenses, Advance, Shift, Salary, SOP, Notifications, Profile, Settings, auth screens
4. **Manager and approval views (~5)** — Team dashboard, Remote approvals, Pending approvals banner
5. **Dialogs (~5)** — Late checkout, Remote check-in, Strict rejection, Push prompt, PDF viewer

**Rule for every Phase 5 prompt:** compose from Phase 2 primitives only. If a screen appears to need a new primitive, stop and raise it against the spec rather than inventing one inline. That single rule is what keeps 41 screens coherent.

**Apply the grid flattening** (spec §15.2) on Leave, Attendance and Issues.

### Phase 6 — Desktop (conditional)
Only if Decision 1 is yes. `SideNav` under Glass, `lg:` breakpoints across all screens.

### Phase 7 — Defects (parallel, 2 prompts)
| # | Prompt |
|---|---|
| 7.1 | 60-second duplicate-submission guard with the `pending` state |
| 7.2 | Night-shift check-in: derive button state from the employee's open shift, not the calendar date |

These are independent of the redesign and can run any time. They're also the two things employees will actually notice working better.

---

## 4. Standing preamble for every prompt

Prepend this to each Claude Code prompt. It's the difference between 45 coherent commits and 45 plausible ones.

```
CONTEXT
Repo: Nastyworldwide-Dev/hrms, branch nz-glass (from nz-version-16)
Stack: Vue 3.5, @ionic/vue 7.4 (mode: ios), frappe-ui, Tailwind 3.4, Vite 5, PWA
Authority: HR_Frappe_Glass_Spec_v1.1.md — sections cited per prompt
Mockup: HR_FRAPPE_Glass_Light_and_Dark_2.html governs values, except the
        seven exceptions recorded in spec §14.4

STANDING RULES
1. No hex literals. No arbitrary Tailwind values. Tokens only.
2. No opacity multipliers on ink tokens (spec §2.5).
3. Chartreuse never sets type on light (spec §2.4).
4. Animate transform and opacity only (spec §15).
5. No mix-blend-mode above any glass surface (spec §7).
6. Max 6 glass surfaces per screen; container + child rows = 1 (spec §15.1).
7. Never nest glass.
8. No spinners (spec §11.2). In-flight uses the pending state (spec §11.4).
9. Every interactive element gets the two-tone focus ring (spec §14.3).
10. Every component ships all applicable states and a /design specimen entry.
11. Do not change business logic, validation, routing or the data model.
12. Copy changes ship as Frappe Translation records, not code edits.

BEFORE FINISHING
- Run the contrast test, the lint gates and the glass-surface counter.
- State which spec sections you implemented and any you could not satisfy.
- Never silently deviate from the spec. Flag and stop.
```

Rule 12 and the last line matter more than they look. The failure mode with a 45-prompt sequence is small silent deviations that each look reasonable and collectively produce a different app.

---

## 5. Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| **Backdrop-root bug** — global light field renders grey fog after every Ionic transition | High if 4.1 is done casually | Spec §3.2 is explicit. Test navigation specifically, not just first paint |
| **`borderRadius: 0` reversal** rounds things nobody intended | Certain | Prompt 1.3 produces a diff report before any visual work |
| **frappe-ui upgrade** breaks 103 files | Unknown until spiked | Spike first. It's a day |
| **Phase 2 gets compressed**, screens built with ad-hoc primitives | High — this is the usual failure | The `/design` route and rule 10 make it visible. Do not start Phase 5 with primitives outstanding |
| **Outdoor legibility fails** on the check-in screen | Medium | Test at midday on the named handset before Phase 5 sign-off, not after |
| **P&C reject the 10px type floor** late | Medium | Get Decision 5 in writing at the gate, with an image |
| **Upstream `hrms` merges** conflict across a rewritten view layer | Certain over time | Accepted cost of the fork route. Keep presentation changes out of logic files |
| **Chartreuse isn't the approved corporate palette** | Unknown | Decision 6. Reversing after Phase 1 is another full token migration |

---

## 6. Ownership

| Work | Suggested |
|---|---|
| Decisions 1, 3, 4 | You |
| Decisions 2, 5, 6 | P&C, packaged as one memo |
| frappe-ui spike | You or Arif |
| P1 Foundation, P4 Shell | You — highest-leverage, most spec-sensitive |
| P2 Primitives | Parallelisable across Arif and Aiman once the specimen route exists |
| P3 Sweep | Mechanical, good candidate for the autonomous pipeline |
| P5 Screens | Parallelisable, one view per prompt |
| P7 Defects | Independent, anyone |
| Sign-off (spec §18) | Per screen, whoever didn't build it |

---

## 7. What happens next

1. Answer Decisions 1, 3, 4 — you can do this today
2. Send P&C the memo covering Decisions 2, 5, 6
3. Run the frappe-ui spike
4. Come back with those results and I'll write Prompt 1.1 through 1.6 in full

The prompts get written after the gate clears, not before — writing them now would bake in assumptions about six unanswered questions.

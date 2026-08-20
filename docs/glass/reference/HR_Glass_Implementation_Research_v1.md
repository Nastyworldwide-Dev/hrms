# HR Frappe · Glass — Implementation Research & Readiness Audit

**Prepared for:** NSTY Holding · IT
**Input:** `HR_FRAPPE_Glass_Implementation_Spec__1_.html` (v1.0, 17 Aug 2026, NSTY Group P&C)
**Target codebase:** `frappe/hrms` → `frontend/` (the Frappe HR employee PWA), branch `develop` as of today
**Status:** research only — no implementation. Output is meant to be the input to the build prompts.

---

## 0. Verdict up front

The spec is unusually good for an HR-issued design document — it has tokens, states, a performance budget and acceptance criteria, which is more than most engineering-led redesigns start with. It is **not yet buildable as written**, for three reasons, in order of severity:

1. **It specifies a design system for an app it doesn't match.** The spec defines 12 components (9 actually documented) across 8 screens. The real PWA has ~40 components across 27 screens, and the ones the spec omits — modal, action sheet, toast, link/autocomplete picker, date picker, calendar, data table, file upload, workflow status — are exactly the ones that carry the visual weight of the app. Building from the spec alone guarantees an incoherent result, because ~60% of the surface would be improvised.
2. **Several rules in the spec contradict other rules in the same spec**, and the accessibility section fails against its own tokens. Most consequentially: the focus ring is specified as `#C8FF00`, which measures **1.11:1** against light glass. Section 11 requires 3:1 for UI components and section 2.3 explicitly bans chartreuse from carrying meaning on light. Two of the spec's own rules break the third.
3. **The current codebase has no token layer at all.** 341 hardcoded Tailwind colour utilities (`bg-white` ×65, `text-gray-800` ×69, …) across 79 `.vue` files, zero dark-mode variants, and every visual decision inlined at the call site. There is nothing to re-theme. This is a rebuild of the view layer, not a restyle — worth saying out loud before anyone estimates it as "apply the new CSS".

None of this is fatal. It means the sequence is: **fix the spec's internal defects → close the component inventory → decide the architecture route → then write build prompts.** Prompting before the first three is how you get 79 files that each look individually plausible and collectively arbitrary.

---

## 1. What you are actually building on

Facts pulled from the `frappe/hrms` source, not from memory.

| Thing | Reality |
|---|---|
| Framework | Vue 3.5 + Vite 5, SPA served at `/hrms` from `hrms/www/hrms.html` |
| UI shell | **`@ionic/vue` 7.4**, configured globally with `mode: "ios"` |
| Design layer | Tailwind 3.4 with the **frappe-ui preset**; no custom theme beyond safe-area padding + a `standalone` screen |
| Component lib | `frappe-ui` 0.1.105 — Button, Input, FormControl, Badge, Dialog, Autocomplete, DateTimePicker, TextEditor, Avatar, Switch, Popover, LoadingIndicator, Toasts, FeatherIcon |
| Data layer | `frappe-ui` resources (`createResource`, `createListResource`) over **17 whitelisted `hrms.api.*` methods** + standard Frappe REST |
| Icons | `feather-icons` (24×24 grid, 2px stroke) + 9 hand-drawn local `.vue` icons |
| Type | `--ion-font-family: "InterVar"` — **Inter is already self-hosted via frappe-ui**, so spec §13's "self-host Inter" is largely already satisfied. Inter Tight is not present. |
| PWA | `vite-plugin-pwa`, `injectManifest`, Firebase push via `frappe-push-notification` |
| Scale | 79 `.vue` files · ~40 components · 27 views |
| Theming | **None.** No dark mode, no CSS custom properties for app colour, no `data-theme` |

### Measured token debt

| Category | Tokens defined today | Hardcoded instances found |
|---|---|---|
| Colour | 0 | **341** utility occurrences (`bg-white`, `text-gray-*`, `text-red-500`, …) |
| Spacing | Tailwind default only | every value inline (`p-4`, `gap-7`, `my-7`, …) |
| Radius | Tailwind default only | inline |
| Elevation | `shadow-sm` / `shadow-md` | inline |
| Dark variants | 0 | n/a |

### Ionic surface that must be dealt with

`IonPage` ×23 · `IonModal` ×19 · `IonContent` ×17 · `IonHeader` ×3 · `IonTabBar`/`IonTabButton`/`IonTabs` · `IonActionSheet` · `IonRefresher` · `IonRouterOutlet`

These are Web Components with Shadow DOM. You cannot reach inside them with Tailwind classes or a stylesheet — only via their published CSS custom properties (`--background`, `--color`, `--border-radius`, `--padding-*`) and `::part()`. Any glass treatment of a page background, modal, sheet or tab bar goes through that channel or not at all.

---

## 2. Spec audit — defects to resolve before any code is written

### 2.1 Contrast: computed, not estimated

I composited the actual token stack (glass fill over light field, and over the brightest blob centre, exactly as §11 instructs) and measured WCAG 2.x ratios.

**Light theme**

| Pair | Ratio | Required | Result |
|---|---|---|---|
| `--ink` `#0B0C10` on glass | 18.40 | 4.5 | pass |
| `--ink2` `#545C68` on glass | 6.36 | 4.5 | pass |
| `--ink2` over chartreuse blob centre | 6.23 | 4.5 | pass |
| `--ink3` `#8A929E` on glass | **2.96** | 4.5 text / 3.0 icon | **fail** — placeholders, captions, chevrons |
| `--accent-ink` `#3F5C00` on glass | 7.21 | 4.5 | pass |
| `#0A0C05` on `#C8FF00` | 16.63 | 4.5 | pass |
| **Focus ring `#C8FF00` vs glass** | **1.11** | 3.0 | **fail — critical** |
| Error text `#F87171` on glass | **2.60** | 4.5 | **fail** |
| Error ring `#F87171` vs glass | **2.60** | 3.0 | **fail** |
| Badge RESOLVED `#00806B` on its tint | **4.09** | 4.5 (7.5px text!) | **fail** |
| Glass rim (white 90%) vs field | **1.13** | 3.0 for control boundaries | **fail** for inputs |

**Dark theme**

| Pair | Ratio | Required | Result |
|---|---|---|---|
| `--ink` on dark glass | 17.38 | 4.5 | pass |
| `--ink2` `#A8AEB8` | 7.79 | 4.5 | pass |
| `--ink3` `#6B7280` | **3.59** | 4.5 text | **fail** as text, passes as icon |
| `#C8FF00` accent text | 14.70 | 4.5 | pass |
| Focus ring `#C8FF00` | 14.70 | 3.0 | pass |
| **`--ink2` over a blob centre** | **1.26** | 4.5 | **fail** |
| **`--ink3` over a blob centre** | **1.73** | 4.5 | **fail** |

**Reading:** the light theme is sound for primary and secondary text and fails for every *tertiary* and *state* colour. The dark theme is sound everywhere except over the light field itself — because dark glass is only 7.5% opaque, text over a blob centre is effectively text on chartreuse. §11 tells you to test exactly there, and exactly there it fails.

**Resolutions to get signed off before building:**
- Focus ring becomes a two-tone ring — 2px `--ink` inner + 3px `#C8FF00` outer, or use `--accent-ink` on light. It must not depend on chartreuse alone.
- `--ink3` splits into `--ink3` (non-text: chevrons, dividers, disabled) and a new `--ink-muted` that actually reaches 4.5:1 (light ≈ `#6E7683`, dark ≈ `#8A929E`).
- Error text/ring gets a darker light-theme value (≈ `#DC2626`) while `#F87171` stays as the dark-theme value. One semantic token, two theme values — same pattern as `--accent-ink`.
- Blob placement becomes a hard constraint: **no blob centre may fall inside the content column**, or the panel over it takes a local scrim. Cheapest fix is to keep all three centres in the negative margins; the spec already does this for A and C but not for B (`bottom:76 right:-58`).
- Badge minimum size rises (see 2.4) and RESOLVED takes a darker ink.

### 2.2 The token layer contradicts itself

§2 says "there are no one-off hex values in components." The spec's own component CSS then hardcodes `#C8FF00` in the focus ring, the balance bar fill, the active tab well, and the banner rule; `#F87171` in the error state; `#00806B` in the light badge; `#F59E0B` in the warning banner. None of these are in the token table — §2.1 lists them as "brand constants", which is a different thing from a token you can reference.

**Fix:** every value in §2.1 becomes a named token (`--brand`, `--brand-2`, `--on-brand`, `--success`, `--leave`, `--danger`, `--warn`), and every component rule references tokens only. This is the single highest-leverage change in the whole document, because it is what makes the "one rule you cannot break" in §2.3 machine-enforceable rather than a thing people remember.

### 2.3 Orphan and inconsistent values

| Issue | Detail | Fix |
|---|---|---|
| Blur variance | Glass recipe says `blur(20px)`, "do not create variants" — the ghost button then uses `blur(18px)` | One value. 20px, or add a documented `--blur-2`. |
| Orphan radius | Banner is 16px; the radius table has 6/9/14/17/19/20/22 and no 16 | Fold banner into `radius-card` (17) or add `radius-banner` |
| Orphan colours | `#00806B`, `#F59E0B` used but untokenised | Tokenise |
| Spacing scale | 9 / 13 / 15 / 16px — no common divisor, not a 4pt grid | **Keep as-is but name them.** Do not "correct" to 8/12/16; the mockup governs. The discipline comes from naming, not from rounding. |
| Type scale | 16 distinct sizes incl. 7.5 / 8.5 / 10.5 / 12.5 / 13.5 / 15.5 / 21.5 | Freeze as an enumerated scale with names; ban any size not on it |

### 2.4 Type sizes below platform minimums

Badge text at **7.5px** and field/micro labels at **8.5px** sit under every platform guideline (Apple HIG floor is 11pt) and under the size at which 0.14em tracking is legible on a mid-range Android at 3× density. This interacts badly with two other requirements:

- §11 demands the layout survive **120% font scaling** — but the shipped `index.html` sets `maximum-scale=1.0, user-scalable=no`, which suppresses user zoom entirely (also a WCAG 1.4.4 failure in its own right).
- Form inputs at 12.5px are below the 16px threshold at which iOS Safari auto-zooms on focus. The existing `maximum-scale=1` masks this today; if you remove it to satisfy §11, focus-zoom appears.

**Also worth flagging as a live bug:** that viewport meta is malformed — `viewport-fit=cover maximum-scale=1.0` is space-separated where the directive list must be comma-separated. `viewport-fit=cover` is what makes `env(safe-area-inset-*)` return non-zero on iOS. §13's safe-area requirement may be unachievable until that line is fixed. Verify on device before designing around it.

**Decision needed from P&C:** raise the floor to 10px/11px, or accept the a11y exception in writing. This is a design-authority call, not an engineering one.

### 2.5 Counting inconsistencies

| Claim | Reality in the document |
|---|---|
| "Twelve components" (§1, §8) | Nine specified: 8.1–8.9. **8.10 and 8.11 do not exist**; numbering jumps to the 8.12 callout |
| "Seven screens" (§1) | **Eight** listed in §10 (Sign in, Home, Check in, Leave, Attendance, Overtime, KPI, Issues) |
| "No new features" (§1 out of scope) | **Overtime, KPI and Issues screens do not exist in the app.** Three new screens, with backing doctypes, workflows and approval routing, is a feature programme — not a visual layer |

That last row is the biggest scoping problem in the document and needs an explicit answer before anything is estimated.

### 2.6 Disabled is being used as two different states

§9.4 requires the primary action to enter its **disabled** state on first tap until the server responds. But disabled is also the state for "you cannot do this yet" (outside shift window, no balance). Same pixels, two meanings — and the disabled treatment measures 2.68:1, so the user gets no legible feedback that their tap registered.

**Fix:** add a third button state — `pending` / in-flight — that keeps the brand fill, replaces the label with a progress affordance, and is announced via `aria-busy`. Note this collides with §9.2's "no spinners anywhere in this app": you need a non-spinner in-flight affordance (indeterminate bar, or label swap to "Sending…"). Decide now, because it affects every form in the app.

### 2.7 Performance budget vs. screen anatomy

The budget is 6 glass surfaces per screen; the anatomy in §10 exceeds it on at least one screen as specified:

- **Leave** = 4 balance cards (2×2) + history list container + tab bar = **6**, before any banner. Add the "unresolved punch" banner pattern and you are at 7.
- **Home** = banner + quick-link panel + 2 balance cards + tab bar = 5, plus a status chip = 6. At the ceiling with no headroom.

**Fix:** define a counting rule ("a glass container and its child rows count as one; a grid of N cards counts as N") and then either raise the ceiling for Leave or make the balance grid a single glass panel with internal dividers. Either is fine; leaving it undefined means each developer resolves it differently, which is precisely the incoherence you're trying to avoid.

---

## 3. The component inventory gap

This is the section that most determines whether the result feels designed or assembled. The spec covers the employee happy path. The app is bigger than that — and manager approval flows run through the same screens.

| # | Needed by the real app | In spec? | Notes |
|---|---|---|---|
| 1 | Primary action | 8.1 | needs `pending` state added (2.6) |
| 2 | Ghost action | 8.2 | blur value conflict |
| 3 | List row | 8.3 | needs variants: with-badge, with-amount, two-line, destructive |
| 4 | Input field | 8.4 | focus ring fails contrast |
| 5 | Balance card | 8.5 | — |
| 6 | Badge | 8.6 | only 2 states; Frappe workflow has ≥6 |
| 7 | Tab bar | 8.7 | 5 items; app has 5 — but restyle vs replace is undecided |
| 8 | Progress ring | 8.8 | KPI screen doesn't exist yet |
| 9 | Banner | 8.9 | — |
| 10 | Empty state | 9.1 | — |
| 11 | Skeleton | 9.2 | one shape specified; needs one per layout archetype |
| 12 | **App header / nav bar** | ❌ | title + notification bell with unread dot + avatar; on every screen |
| 13 | **Back / detail header** | ❌ | 23 pages use it |
| 14 | **Modal / bottom sheet** | ❌ | **19 usages** — the most-used surface in the app after the row |
| 15 | **Action sheet** | ❌ | request actions, workflow actions, list filters |
| 16 | **Toast** | ❌ | every submit outcome lands here |
| 17 | **Link / autocomplete picker** | ❌ | Frappe link fields; searches server-side |
| 18 | **Date & datetime picker** | ❌ | leave, attendance, OT — the highest-friction control in the app |
| 19 | **Textarea / rich text** | ❌ | reason fields |
| 20 | **File upload + preview** | ❌ | expense receipts, check-in selfie |
| 21 | **Avatar** | ❌ | header, profile, approver rows |
| 22 | **Calendar** | ❌ | §10 says "calendar panel" with no component spec |
| 23 | **Segmented control** | ❌ | in-page tabs (`TabButtons`) |
| 24 | **Data table** | ❌ | payslip earnings/deductions, expense lines — and §8.12 says these must not be glass |
| 25 | **Chart** | ❌ | leave balance semicircle |
| 26 | **Pull-to-refresh** | ❌ | Ionic-owned; needs theming |
| 27 | **Workflow status chip** | ❌ | Draft / Submitted / Approved / Rejected / Cancelled — colour+word mapping needed |
| 28 | **Search / filter bar** | ❌ | list views |
| 29 | **Auth screens set** | partial | Sign in specified; forgot-password, change-password, invalid-employee not |
| 30 | **PWA install prompt** | ❌ | exists today, will look foreign |

**Screens in the app the spec never mentions:** Expense Claim (dashboard/list/form), Employee Advance (list/form), Shift Request, Shift Assignment, Salary Slip detail, Notifications, Profile, App Settings, Change Password, Forgot Password, Invalid Employee. That is 11+ screens that will otherwise be built by pattern-matching.

**Recommendation:** before prompting, produce a **component contract sheet** — for each of the 30 rows: name, tokens consumed, variants, all six states (populated / empty / loading / error / disabled / offline), a11y role + announced string, and the props API. That artefact is what makes parallel implementation coherent. It is also exactly what a build prompt should be pointed at, one component at a time.

---

## 4. Technical risks specific to glass on this stack

### 4.1 The backdrop-root trap — highest risk item

`backdrop-filter` in Chromium filters only the contents of its **current isolation group**. Any ancestor carrying `opacity`, `filter`, `transform`, `will-change` or `mix-blend-mode` becomes a backdrop root, and the blur stops seeing anything above it. <cite index="4-1">Chrome's implementation makes backdrop-filter respect isolation boundaries, taking as input only the contents of the current isolation group up to that element</cite> — and developers hitting this in production report having to move backdrop-filter onto pseudo-elements and avoid animating opacity on ancestors specifically in mobile layouts.<cite index="1-1">One report describes conditionally not animating opacity in the mobile layout that uses backdrop-filter, and setting all backdrop-filter on pseudo-elements, to avoid making the connected element a backdrop root</cite>

**Why this bites you specifically:** Ionic's `ios` page transitions animate `transform` and `opacity` on `.ion-page`. If the light-field blobs live outside the page element (e.g. on `ion-app` or `body`) and the glass panels live inside it, then during and after transitions the glass will blur *nothing* and render exactly as the "grey fog" §2.4 warns about.

**Implication for the token/DOM contract:** the light field must live **inside the same stacking context as the glass**, i.e. per-page, beneath the content layer — not a global background. This is a structural rule that belongs in the spec and currently isn't there. It also means each page carries its own 3 blobs, which interacts with the 6-surface budget.

### 4.2 Ionic shadow DOM: what is reachable

| Surface | How you theme it |
|---|---|
| `ion-content` | `--background: transparent` to let the page's light field show through; `--padding-*` |
| `ion-tab-bar` | host is stylable (position, border-radius, width, margin); interior via `--background`, `--color`, `--color-selected`. The floating-pill pattern (radius 22, inset from edges, above safe area) is a known, achievable Ionic customisation |
| `ion-modal` | `--background`, `--border-radius`, `--backdrop-opacity`, `--height` (already overridden to `auto` in `main.css`) |
| `ion-action-sheet` | CSS vars + `::part()` |
| `ion-refresher` | limited; likely needs replacing to match |
| Anything else | `::part(native)` where exposed, otherwise not reachable |

**Open architectural question:** keep `ion-tabs` for its per-tab navigation stacks and restyle the bar, or drop to `ion-router-outlet` + a custom tab bar and lose stack-per-tab. Restyling is less work and keeps Ionic's routing semantics; a custom bar gives exact control of the glass. Recommend restyle first, replace only if the pill can't be reached cleanly.

### 4.3 frappe-ui's components are not themeable into this system

frappe-ui's Button/Input/Dialog/Badge carry their own visual language (neutral greys, ~8px radii, light-only) as hardcoded Tailwind classes. They cannot be tokenised into glass from outside.

**Recommendation:** keep frappe-ui for **data and behaviour** (`createResource`, `createListResource`, `toast`, `Autocomplete`'s search logic) and replace its **presentational** components with your own primitives. Do not attempt to override them with `!important` cascades — that path produces the exact incoherence this project exists to prevent. Note `LoadingIndicator` (a spinner) appears 7 times and must go under §9.2.

### 4.4 Tailwind mapping

- Tailwind 3.4 + frappe-ui preset. Tokens go into `theme.extend` as **semantic names** (`bg-glass`, `text-ink-2`, `rounded-panel`, `shadow-lift`) referencing CSS custom properties — never raw values in templates, never `bg-white/[0.075]`.
- Dark mode: `darkMode: ["class", '[data-theme="dark"]']` so the spec's `data-theme` attribute drives Tailwind variants and CSS vars from one switch.
- Add a small plugin for the composite recipes: `.surface-glass`, `.surface-solid`, `.field-light` — so the glass recipe exists in exactly one place, as §5 requires.
- Enforce with a lint rule banning hex literals and arbitrary values (`[...]`) in `.vue` files. Without a CI gate, "no one-off hex" is a wish.

### 4.5 Other stack-level items

| Item | Note |
|---|---|
| `theme-color` meta + manifest `theme_color` are `#ffffff` | Must become theme-aware, or the status bar fights dark mode |
| PWA splash screens | Light-only; a dark-launch flash will be visible |
| `@supports not (backdrop-filter: blur(1px))` fallback | Spec provides values — good. Also need `will-change` discipline and to avoid `filter` on ancestors (4.1) |
| Reduced motion | Must also disable Ionic's page transitions, not just your own CSS |
| Theme switch at 400ms | Transitioning colour on every node while `backdrop-filter` recomposites is expensive. Scope the transition to a wrapper, or suppress it during switch |
| Translations | `translationsPlugin` reads `frappe.boot.__messages` and supports context. **All of §10.1's copy changes can ship as Frappe Translation records — zero code change.** Caveat: keying on the source string may leak the new wording into Desk; use context, or scope to the app |
| Offline | A service worker exists; §9.3's offline states need a defined source of truth for connectivity |

---

## 5. Architecture routes

| Route | What it is | Pros | Cons |
|---|---|---|---|
| **A. Fork `hrms`** | Branch `hrms`, rewrite `frontend/` in place | Reuses routes, data, API; nothing new to maintain server-side | Every upstream `hrms` release conflicts with 341 changed lines across 79 files. On Frappe Cloud, upgrades become a manual merge forever. High long-term cost |
| **B. New custom app** | `nsty_hr` Frappe app with its own Vue PWA at `/nstyhr`, consuming the same 17 `hrms.api.*` methods + REST | Clean-room design system; no fork; `hrms` upgrades freely; you can drop Ionic and its shadow-DOM constraints entirely | Must re-implement screen logic; must track upstream API changes; duplicated routing/permission plumbing; longer to first ship |
| **C. CSS override only** | Ship a stylesheet that retargets built classes | Cheapest | **Not viable.** Utilities are compiled per-element; glass needs DOM structure (light field, panel nesting) that CSS cannot add. Also `app_include_css` doesn't reach an SPA bundle |
| **D. Fork + token refactor** | Fork, but first mechanically replace all 341 utilities with token-backed semantic classes, then restyle | Diffs become predictable; upstream merges touch logic, you touch presentation | Still a fork; requires discipline to keep the boundary clean |

**Recommendation:** **B if this is a long-lived group product; D if it must ship this quarter.** The deciding question is not technical — it's whether NSTY intends to track upstream Frappe HR features (payroll changes, new leave types, tax updates) or freeze on a version. If you intend to keep upgrading, do not fork the view layer of an app you upgrade.

A defensible middle path: build the **design system package first** (tokens + primitives + specimen page) as its own repo/workspace, independent of either route. It's the same work in both, it de-risks the decision, and it's the thing that makes the result coherent regardless of where it's mounted.

---

## 6. What "coherent and disciplined" requires operationally

Design coherence at this scale is not achieved by care; it's achieved by making incoherence fail a check.

1. **One token source of truth** — a `tokens.json` that generates both the CSS custom properties and the Tailwind theme. Nobody edits CSS vars by hand.
2. **A naming convention, written down** — semantic, not descriptive (`--surface-glass`, not `--white-56`). Descriptive names are why dark mode retrofits fail.
3. **A primitive layer with an explicit API contract** — ~30 components, each with the states table from §3. Nothing in a screen may style itself; screens compose primitives only.
4. **A live specimen route** (`/design`) inside the app, in both themes, on device. The spec's HTML specimens are the right idea; they need to live in the app so they can't drift.
5. **CI gates**, in order of value:
   - lint: no hex literals, no arbitrary Tailwind values, no `outline: none` without a replacement, no raw `ion-*` styling outside the theme layer
   - contrast unit test over the token matrix — the table in §2.1 as an assertion, run on every change to `tokens.json`
   - Playwright visual regression per component per theme at 390×844
   - axe pass per screen
   - a glass-surface counter per screen against the §12 budget
6. **Definition of done per component**, not per screen — all six states, both themes, focus ring, screen-reader string, reduced-motion behaviour, and a specimen entry.

---

## 7. Suggested sequencing

Each phase should be independently shippable and independently promptable.

| Phase | Output | Gate |
|---|---|---|
| **0. Spec amendment** | v1.1 of the spec resolving §2 of this document (contrast, tokens, states, counts, scope) | P&C sign-off on the type-size floor and the Overtime/KPI/Issues scope question |
| **1. Foundation** | `tokens.json` → CSS vars + Tailwind theme; `data-theme` switch; light-field structure rule; lint + contrast tests in CI | Contrast matrix green in both themes |
| **2. Primitives** | ~30 components + `/design` specimen route, all states, both themes | Visual regression baseline captured |
| **3. Shell** | Header, tab bar, page scaffold, modal, action sheet, toast; Ionic theming layer; safe-area + viewport-meta fix | 60fps on the lowest-spec device in the fleet |
| **4. Screen migration** | Existing 27 views, in dependency order (Home → Attendance → Leave → Expense → Salary → Profile/Settings) | Per-screen QA checklist from spec §14 |
| **5. Defects** | Duplicate-punch guard (§13.1), night-shift check-in state (§13.2) | Reproduced-then-fixed evidence |
| **6. New screens** | Overtime, KPI, Issues — only if scoped in Phase 0 | Separate spec + backend design |

Phases 1–2 are where the coherence is won or lost, and they are the ones most likely to be skipped under schedule pressure.

---

## 8. Open decisions — needed before prompts can be written

1. **Architecture route** — B (new app) or D (fork + refactor)? Everything downstream depends on this.
2. **Scope of Overtime / KPI / Issues** — in this programme, or deferred? If in: what are the backing doctypes (custom OT doctype? Appraisal for KPI? Issue/HD Ticket?), and who owns the workflow design?
3. **Type-size floor** — hold 7.5/8.5px as drawn, or raise to 10/11px? P&C decision, affects badge, field labels, micro labels, tab labels.
4. **Chartreuse focus ring** — accept a two-tone ring, or a different accent on light? The spec cannot ship as written either way.
5. **In-flight state** — indeterminate bar, label swap, or an exception to "no spinners"?
6. **Ionic tab bar** — restyle host, or replace and give up stack-per-tab navigation?
7. **Uncovered screens** — does the design system extend to Expense Claim, Advance, Shift, Salary, Profile, Settings, Notifications now, or do they stay unstyled in phase 1?
8. **Manager/approver flows** — same visual system, or out of scope? Currently unmentioned in the spec.
9. **Copy changes** — ship as Frappe Translation records (recommended, zero code) with context scoping, or hardcode in the frontend?
10. **Device floor** — which specific handset is "the lowest-spec device in the fleet"? §12 and §14 both reference it; the budget is meaningless without a named model.

---

## 9. What I'd need from you to write the build prompts

- The answers to §8 (at minimum 1, 2, 3, 4).
- The paired mockup `HR_FRAPPE_Glass_Light_and_Dark.html` — the spec says the mockup governs where they disagree, so I can't resolve conflicts without it.
- Whether your target site runs `hrms` from Frappe Cloud (upgrade cadence not in your control) or self-hosted/bench (you control the version).
- Confirmation of the `hrms` version deployed at NSTY, since I audited `develop`.
- Whether the Claude Code pipeline will build this component-by-component (recommended — one component contract per prompt) or screen-by-screen.

---

*Research prepared against `frappe/hrms@develop`. Contrast figures computed from the spec's own token values composited per §11's instruction. No implementation performed.*

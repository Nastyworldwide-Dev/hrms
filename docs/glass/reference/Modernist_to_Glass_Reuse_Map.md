# Reuse & Migration Map — Modernist → Glass

**Scope:** what already exists on `nz-version-16` that Glass can reuse, what gets reskinned, what has to be new.
**Companion to:** `HR_Glass_Implementation_Research_v1.md` and the `nz-version-16` addendum.
**Caveat:** written without `HR_FRAPPE_Glass_Light_and_Dark.html`. Where the spec is ambiguous I've marked the row **[verify vs mockup]**. The spec says the mockup governs, so these rows are provisional.

---

## 1. The reuse principle

Three buckets, and the sorting rule matters more than the individual verdicts:

| Bucket | Rule | What you do |
|---|---|---|
| **Keep** | The file carries behaviour, not appearance | Don't touch. Zero visual risk, zero migration cost |
| **Reskin** | The DOM structure survives the aesthetic change — same slots, same props, different classes | Swap classes. Highly promptable, one file per prompt |
| **Replace** | The aesthetic is load-bearing in the structure — flat/0-radius is encoded in the markup, not just the classes | Rewrite against a Glass component contract |

The failure mode to avoid: treating a **Replace** as a **Reskin**. That's how you end up with a rounded, translucent version of a flat brutalist component — which reads worse than either system done properly, and is exactly the incoherence you asked me to guard against.

---

## 2. Primitive layer — `.m-*` → Glass

You have 14 primitive classes and ~150 usages. Glass needs roughly 30. Nine of the fourteen map cleanly.

| Modernist | Usages | → Glass component | Verdict | What changes |
|---|---|---|---|---|
| `.m-btn-primary` | 7 | **8.1 Primary action** | **Reskin** | Same flex/space-between/trailing-arrow structure — the spec's `<b>LABEL</b><span>→</span>` is the identical shape. Add gradient fill, 19px radius, brand shadow, `press` transform, and the new `pending` state |
| — | — | **8.2 Ghost action** | **New** | Modernist has no secondary button. Derive from `.m-btn-primary` structure with the glass recipe |
| `.m-row` | 2 | **8.3 List row** | **Reskin** | Currently a bare bottom-border. Needs the 27×27 icon well, 11px gap, 15px-inset hairline, 44px min-height, tap state |
| `.m-field-input` / `.m-field-label` | 5 / 6 | **8.4 Input field** | **Reskin** | Structure fine. Needs 14px radius, glass fill, rim, focus ring (redesigned — see contrast findings), error state |
| `.m-statnum` + `.m-bar` + `.m-bar-band` | 1 + 2 + 1 | **8.5 Balance card** | **Reskin, keep the band** | `.m-bar-band` — the hatched pro-rated headroom tail — is genuinely good product thinking and the Glass spec has no equivalent. **Keep it.** Spec §8.5 gives you a 3px bar; the band survives as a second layer. Numeral goes 28px→31px, weight/tracking per §3.1 |
| `.m-chip` + solid/outline/muted | 63 total | **8.6 Badge** | **Reskin** | Three variants → the spec only defines two (OPEN, RESOLVED). Your three-variant model is better; extend the spec rather than losing it. Size drops 10px→7.5px **[flag: contrast + legibility, see audit §2.1/2.4]** |
| `.m-tab-bar` + `.m-tab-btn` | 2 + 2 | **8.7 Tab bar** | **Reskin** | Ionic shadow-DOM theming already solved. Changes: floating pill (22px radius, inset from edges), glass fill, the 3px top indicator becomes the glowing well, 8 items → 5 |
| — | — | **8.8 Progress ring** | **Check first** | `SemicircleChart` existed upstream; confirm what `kpi/Dashboard.vue` renders today before building new |
| — | — | **8.9 Banner** | **Reskin from** `PendingApprovalsBanner` | The 3px left rule maps to your existing accent-bar pattern |
| `.m-kicker` | **52** | **§3.1 Eyebrow** | **Reskin** | Most-used primitive in the codebase. 10px/0.1em → 10.5px/0.13em, Archivo 800 → display 600. One class, 52 sites fixed |
| `.m-rule` | 6 | divider | **Replace** | 2px block rule is pure Modernist. Glass uses 1px `--hair` |
| `.m-poster` | 1 | — | **Retire** | Inverted accent block; no Glass analogue |
| `.m-avatar-sq` | 6 | avatar | **Invert** | It exists solely to force frappe-ui's Avatar to 0 radius. Under Glass you want the rounding back — this class gets deleted, not rewritten |
| `.m-chip-*` colour model | — | workflow status | **Extend** | Neither system defines Draft/Submitted/Approved/Rejected/Cancelled. Needed either way |

**Net:** 9 of 14 primitives reskin, 1 keeps a feature Glass lacks, 1 gets deleted outright, 1 retires, and ~16 new primitives are needed. The token mechanism underneath (`--m-*` triplets + `<alpha-value>`) survives entirely — rename to `--g-*` and swap values.

---

## 3. Component layer — by usage, highest first

| Component | Used in | Verdict | Note |
|---|---|---|---|
| `ResourceError` | **21** | **Keep + reskin** | Already the error surface the spec asks for in §9.3. Highest-leverage single reskin in the app |
| `EmptyState` | **15** | **Reskin** | 17 lines. Currently one line of grey text; §9.1 wants title + body + dashed rim + a per-screen copy table. Small file, big visible upgrade |
| `BaseLayout` | 10 | **Replace** | The page shell has to change structurally — the per-page light field lives here (see backdrop-root finding), plus header + safe-area |
| `ListItem` | 8 | **Keep** | Pure slot container (`left`/`right`), no aesthetic. Untouched |
| `FormView` | 8 | **Reskin** | Form chrome; check overlap with `FormShell` |
| `ListView` | 7 | **Reskin** | Row container + glass panel wrapper |
| `RequestList` | 4 | **Reskin** | — |
| `FormField` | 4 | **Keep logic, reskin skin** | 251 lines dispatching by Frappe fieldtype into frappe-ui Autocomplete/Link/TextEditor. **The dispatch logic is the valuable part — do not rewrite it.** Replace only the label markup and the field wrappers |
| `TabButtons` | 3 | **Reskin** | Segmented control. Glass spec doesn't define one — extend |
| `FormattedField` | 3 | **Keep** | Value formatting, no appearance |
| `EmployeeAvatar` | 3 | **Reskin** | Drop `.m-avatar-sq`, restore rounding |
| `CustomIonModal` | 3 | **Keep** | Wraps a real Ionic focus-trap bug (#24646) with a custom backdrop. **This is hard-won knowledge — do not "clean it up".** Reskin via CSS vars only |
| `WorkflowActionSheet`, `RequestActionSheet`, `ListFiltersActionSheet` | 2/2/1 | **Reskin** | Sheet surface theming is centralised in `modernist.css` already |
| `SideNav` | 2 | **Decision pending** | Desktop is out of Glass scope as written |
| `FilePreviewModal`, `PdfInlineViewer`, `FileUploaderView` | 2/1/1 | **Reskin** | — |
| `LateCheckoutDialog`, `RemoteCheckinDialog`, `StrictRejectionDialog` | 1 each | **Reskin** | All three map to §9.3 error/permission states |
| `CheckInPanel`, `LeaveBalance`, `QuickLinks`, `RequestPanel` | 1 each | **Replace** | These are the Home screen, and §10 specifies its stack order precisely. Rebuild against the anatomy |
| `AttendanceCalendar` | 1 | **Reskin** | No Glass spec exists for a calendar — needs a contract first |
| Tables (`ExpensesTable`, `SalaryDetailTable`, `ExpenseTaxesTable`, `ExpenseAdvancesTable`) | 1 each | **Reskin — solid only** | §8.12: payslip and expense figures must sit on the most opaque surface. **No glass on these** |

---

## 4. Infrastructure to keep untouched

These already exist, already work, and are the sort of thing that gets casually deleted during a restyle and then re-debugged for a week:

| Asset | Where | Why it stays |
|---|---|---|
| Theme store — light/dark/system, persisted, View Transitions circular reveal | `data/theme.js` | Exactly what spec §11 ("theme follows system with a persisting override") requires, already built |
| `theme-color` meta swap | `data/theme.js` | Status bar matching per theme |
| Autofill repaint fix | `modernist.css` | Chrome paints autofilled inputs near-white; without this, dark-mode login is white-on-white |
| Global `prefers-reduced-motion` block | `modernist.css` | Spec §6 requirement, already satisfied |
| Ionic tab bar shadow-DOM theming + `contain: content` | `BottomTabs.vue` | The `height:auto` fix stops Ionic's fixed 50px bar clipping |
| Desktop sheet-as-popup rule | `modernist.css` | `ion-modal` centred at ≥640px |
| Safe-area padding utilities | `tailwind.config.js` | Already wired |
| `frappe-ui` data layer | throughout | `createResource` / `createListResource` / `toast` — keep all of it |

**Note:** the reduced-motion block uses `animation-duration: 0.001ms !important` globally. Under Glass that will also kill the skeleton shimmer (§9.2 wants it to become a *static fill*, which this achieves) and Ionic page transitions (fine). Verify it doesn't break the View Transitions reveal.

---

## 5. Genuinely new — no existing counterpart

| Needed | Why nothing maps |
|---|---|
| **The glass recipe itself** (`.g-surface`) | Zero `backdrop-filter` usage anywhere in the codebase today |
| **The light field** (3 blobs, per page) | New structural layer; must live inside the page's stacking context |
| **Skeleton loader** (§9.2) | You use `LoadingIndicator` spinners in 7 places; §9.2 bans spinners outright |
| **Ghost action** (§8.2) | No secondary button exists |
| **Pending / in-flight button state** | Needed for the §9.4 duplicate-punch guard, and it can't be a spinner |
| **Workflow status chips** | Draft / Submitted / Approved / Rejected / Cancelled |
| **Focus ring** | No visible focus treatment exists today; spec's chartreuse ring fails contrast and needs redesign first |

---

## 6. On "looks outdated" — worth being precise

Modernist isn't a dated system; it's a deliberate one (flat, 0-radius, Archivo 800, uppercase tracking — a current editorial/brutalist idiom). So before the migration is framed as "fix the old look", it's worth separating two possibilities, because they lead to different work:

- **Production is still on pre-Modernist upstream** (grey Tailwind defaults, `bg-white` cards, feather icons) — in which case Modernist is unshipped work sitting in a branch, and Glass is the *second* redesign of a screen set that never shipped the first.
- **Production is on Modernist and it reads as flat/severe to people** — in which case the specific properties causing that are the 0-radius, the 2px hard dividers, the uppercase-everything, and the low-chroma warm palette. Glass fixes all four, which is a reasonable diagnosis.

Either way, the reuse map above holds. But the first case has a scheduling implication worth surfacing: you'd be paying migration cost twice on the same files, and it may be cheaper to take Glass straight to the screens that haven't been Modernist-migrated yet rather than reskinning them twice.

---

## 7. Suggested prompt granularity

Given the map, the natural prompt unit is:

1. **One prompt: token generation.** `tokens.json` → `glass.css` + `tailwind.config` colours + `variables.css`. Retires the 3-way manual sync. Includes the deliberate `borderRadius` restoration and an audit of what it silently rounds.
2. **One prompt per primitive** (~30). Each carries: tokens consumed, all six states, a11y string, and its specimen entry. These are small and parallelisable.
3. **One prompt: the arbitrary-value sweep.** 303 `[...]` values across 103 files — mechanical, and best done *after* the scale exists so values have somewhere to go.
4. **One prompt: `BaseLayout` + light field.** The backdrop-root structure. Everything visual depends on this being right.
5. **One prompt per screen** (41 views), in dependency order, each pointed at its §10 anatomy row.

Prompts 1, 2 and 4 must land before any of 5, or each screen prompt will invent its own primitives.

---

## 8. Still blocked on

- `HR_FRAPPE_Glass_Light_and_Dark.html` — needed to resolve every **[verify vs mockup]** row and to settle the spec's own contradictions, since it governs.
- Which of the two scenarios in §6 is true.
- The five open decisions from the addendum (tab count, desktop, type floor, focus ring, in-flight affordance).

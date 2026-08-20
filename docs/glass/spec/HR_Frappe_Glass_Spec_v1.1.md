# HR Frappe · Glass — Implementation Specification v1.6

**Supersedes** v1.5, v1.4, v1.3, v1.2, v1.1 (20 Aug 2026) and v1.0 (17 Aug 2026). The filename stays `…_v1.1.md`: it is referenced by CLAUDE.md, the build prompts and every HANDOFF, and a rename buys nothing. §0 carries the version.
**Sources reconciled:** `HR_FRAPPE_Glass_Light_and_Dark_2.html` (mockup, governing) · `HR_FRAPPE_Glass_Implementation_Spec__1_.html` (v1.0) · `Nastyworldwide-Dev/hrms@nz-version-16` (target codebase).
**Owner:** NSTY Group P&C · **Implementer:** NSTY IT
**Status:** amended for build. Sections marked **[DECISION]** require sign-off before the work they govern begins.

---

## 0. What changed, and why

### v1.1 — from v1.0

| # | Change | Reason |
|---|---|---|
| 0.1 | Five values corrected to the mockup | v1.0 drifted from the mockup it defers to |
| 0.2 | Token count corrected 12 → **15 flipping + 9 constants**, all named | v1.0 banned one-off hex values while using nine of them |
| 0.3 | Contrast failures fixed with **measured** replacement values | v1.0's focus ring measured 1.11:1 against its own 3:1 requirement |
| 0.4 | Type floor raised to **10px** | 7.5px and 8.5px fail on a 390px phone in warehouse lighting |
| 0.5 | New §7: **presentation material vs app material** | The mockup's grain layer would silently disable every `backdrop-filter` in the app |
| 0.6 | Component inventory rebuilt: 9 documented → **28 specified** | v1.0 covered ~a third of the mockup and a fifth of the app |
| 0.7 | Screen count corrected 7 → **8**; scope corrected — OT, KPI and Issues **already exist** | v1.0 listed them as new features; they are built with backing doctypes |
| 0.8 | Navigation resolved to five fixed destinations | The mockup implies six destinations in five slots |
| 0.9 | Glass budget: counting rule added, grids flattened | Three screens sat at the ceiling before any state was added |
| 0.10 | Added **reduce-transparency mode** and the blob-placement constraint | CSS cannot do adaptive contrast; the field is the only control we have |
| 0.11 | Implementation section rewritten for the real codebase | v1.0 assumed a greenfield; a token system (Modernist) already ships |

### v1.2 — rulings raised during the phase 2 build

Each of these was a conflict found while building the components, not a change of intent. They are recorded so the conflict does not survive to be re-derived.

| # | Change | Reason |
|---|---|---|
| 1.1 | Desktop **in scope**; new §20 governs `lg:` | DECISION 1 resolved — HR admin and managers use desktop regularly (§1, §13.3, §19) |
| 1.2 | §6.3 stated to **override the §10 component entries**; `--track-solid` token added for the KPI ring, KRA and balance bar tracks | §10.1 #6/#9 named `--icon-bg`, a translucent value, for tracks §6.3 forbids being translucent. The entries described the visual; they did not grant an exemption |
| 1.3 | §4.2 **scale closed**; four §10.2 entries corrected to their nearest step | Four component entries named sizes the scale does not contain (13, 15, 23px), so every implementer had to invent a resolution. 10.5px was already a step and only needed naming |
| 1.4 | §15.3 added: **chrome counted separately**; the app header is **not** a glass surface, the tab bar **is** | §15.2's arithmetic never counted a header, leaving its material undefined. A glass header above glass content would also nest, which §15 forbids |
| 1.5 | §20.7 gains **#24 App header** — avatar hidden, kicker shown at `lg:` | The v1.1 list was incomplete: the shipped header already differs at `lg:`, so "identical at both breakpoints" was untrue on arrival |
| 1.6 | §10.2 #21 records the **only §2.5 exemption** — clock seconds, with its measured 4.26:1 and the condition that voids it | An unrecorded opacity multiplier reads as an oversight and gets "fixed" or copied; both outcomes are wrong |

### v1.3 — rulings raised by the phase 3 inventory

Both follow from `docs/glass/phase3-inventory.md`, which measured what earlier
sections had estimated.

| # | Change | Reason |
|---|---|---|
| 2.1 | §16.3: the **`--ion-color-*` ramps are not deleted**. Only background, text and font-family map to Glass | The ramps are Ionic's internal contract, not app design tokens. No Glass token corresponds to a shade or tint step, so deleting them breaks `color="primary"` and buys nothing |
| 2.2 | §16.2: file counts corrected — `rounded-*` touches **4 app files, not 103**; arbitrary values are **403, not 303** | Both figures were estimates that drove planning. The measured radius exposure is 106 utilities across 47 `frappe-ui` components, not app source |
| 2.3 | §16.2: the radius scale is **remapped onto the Glass ladder**, not restored to Tailwind defaults and not left at 0 | At 0, frappe-ui renders square against rounded Glass surfaces; at Tailwind defaults it renders off-ladder. Remapping makes 17 third-party components inherit Glass-consistent rounding without touching one of them |
| 2.4 | §10.3 #28: the workflow state set is **open, not five states**; sixteen known states map onto six variants, unknowns render neutral | The five-state list predated reading the code. Real states are composite ("Approved & Unpaid") and Frappe workflows are user-configurable, so a closed validator rejects valid data |
| 2.5 | §10.1 #1 gains a **`trailing` slot** for the mockup's arrow affordance | The arrow is in the mockup's primary action. Without a slot every call site kept a hand-rolled `<button>`, which is the seam the component library exists to close |

### v1.4 — the light field, corrected against its own constraint

| # | Change | Reason |
|---|---|---|
| 3.1 | §3: blob origins corrected — A `left −46→−180`, B `right −58→−163`, C `left −30→−137`. A note now states the values are **box origins** and that §3.3 constrains **centres** | An authoring error in v1.1: the origins were read as centres, so all three centres sat inside the content column and §3 violated §3.3 in the same document |
| 3.2 | §3.3: the rule is **clearance beyond the gradient reach**, not centre-placement alone; per-blob values recorded (A 80px, B 73px, C 62px) | A centre exactly outside the column still fails, and so does a 20px margin. The gradient is ~80px wide, so the constraint has to be measured against it |
| 3.3 | §3.3: states that **vertical needs no equivalent rule**, with the reason | The column is horizontal and full-height, so `x` clearance alone is necessary and sufficient. Recorded so nobody re-derives it |
| 3.4 | §14.4 gains **exception 8**, with before/after measurements | The mockup's values failed §14; that is exactly what §14.4 exists to record |
| 3.5 | The §14.2 pair skipped in phase 1 as "blob not a token" is now **asserted** in `design/gates/contrast.mjs` | The blob is a token as of 4.1, so the prose constraint became a check. It caught this defect |

### v1.5 — anatomy reconciled with the shipped app

| # | Change | Reason |
|---|---|---|
| 4.1 | §12 Home: **balance grid removed**, **request panel added** | The mockup drew a balance grid the shipped Home has no data for and no call to fetch; building it is a feature (§1). The request panel is on the screen and the anatomy omitted it |
| 4.2 | §12 gains a note: anatomies were transcribed from the mockup and **diverge in both directions**; the app governs SCOPE, the anatomy governs LAYOUT | Found while building batch 1. Unlikely to be the only one, so the rule is stated once rather than re-litigated per screen |

### v1.6 — surface counting corrected to what composites

| # | Change | Reason |
|---|---|---|
| 5.1 | §15.1: a sheet's contents are **their own surface set**, asserted against the same limit while presented; the parent screen does not inherit them | A closed `ion-modal` renders nothing. Counting its contents put Home at 5 of 6 for a screen that shows three surfaces, and would eventually block a legitimate build |

---

## 1. Scope

### In scope
- The visual layer of the HR Frappe employee PWA at `/hrms`, both themes
- 28 components with every interactive state
- 8 screens with layout anatomy and stack order
- Empty, loading, error, offline and pending states — **not in the mockup, built to this document**
- Accessibility and performance acceptance criteria
- Desktop layout at `lg:` — no mockup exists; **§20 is the reference** (DECISION 1 resolved, §13.3)

### Out of scope
- Any change to business logic, validation, approval routing or data model
- New features. **Overtime, KPI, Issues, SOP, Team and Remote Approvals already exist** — they are restyled, not built

### Definition of done
A screen is complete when it matches the mockup at 1× on 390 × 844, passes §14, stays inside §15, and switches theme without layout shift.

### Conflict rule
Where this document and the mockup disagree on a **value**, the mockup governs. Where the mockup fails a criterion in §14, **§14 governs** and the exception is recorded in §14.4. There are eight such exceptions and they are listed.

---

## 2. Design tokens

Every colour comes from this section. There are no one-off hex values in components. All values below are verified — the contrast column in §14 is generated from them.

### 2.1 Constants — identical in both themes

| Token | Value | Used for |
|---|---|---|
| `--brand` | `#C8FF00` | Action fill, active indicators, progress fill |
| `--brand-2` | `#A8DC00` | Action gradient end |
| `--on-brand` | `#0A0C05` | Text and icons on brand fill |
| `--success` | `#00E5C0` | Resolved / approved |
| `--leave` | `#7B5CFF` | On leave |
| `--danger` | `#F87171` | Error — **dark theme only**, see 2.3 |
| `--warn` | `#F59E0B` | Warning — **dark theme only**, see 2.3 |
| `--rest` | `#B6BDC9` | Rest day, calendar legend |
| `--neutral-dot` | `#8A929E` | Legend and decorative markers |

### 2.2 Themed tokens — 16 values flip

| Token | Dark | Light | Used for |
|---|---|---|---|
| `--bg` | `#07070A` | `#EDEFF3` | App background beneath the light field |
| `--ink` | `#FFFFFF` | `#0B0C10` | Primary text, numbers, headings |
| `--ink2` | `#A8AEB8` | `#545C68` | Secondary text, labels, captions |
| `--ink3` | `#6B7280` | **`#878F9B`** | **Non-text only** — chevrons, dividers, disabled. Light value raised from `#8A929E` to clear 3:1 |
| `--ink-muted` | **`#7D838F`** | **`#6C727B`** | **New.** Tertiary *text* — placeholders, ticket IDs, timestamps |
| `--accent-ink` | `#C8FF00` | `#3F5C00` | Accent **text only** — see 2.3 |
| `--accent-glow` | `rgba(200,255,0,.45)` | `rgba(63,92,0,.14)` | Glow behind hero numerals |
| `--glass-fill` | `rgba(255,255,255,.075)` | `rgba(255,255,255,.56)` | Panel fill |
| `--glass-rim` | `rgba(255,255,255,.14)` | `rgba(255,255,255,.90)` | Panel border, 1px |
| `--rim-hi` | `rgba(255,255,255,.28)` | `rgba(255,255,255,.95)` | Inset highlight, top edge |
| `--rim-lo` | `rgba(0,0,0,.28)` | `rgba(16,22,34,.06)` | Inset shadow, bottom edge |
| `--lift` | `0 8px 26px rgba(0,0,0,.34)` | `0 10px 30px rgba(20,26,40,.10)` | Panel drop shadow |
| `--hair` | `rgba(255,255,255,.075)` | `rgba(16,22,34,.08)` | Row dividers |
| `--icon-bg` | `rgba(255,255,255,.10)` | `rgba(16,22,34,.05)` | Icon wells, progress tracks |
| `--sheen` | `rgba(255,255,255,.13)` | `rgba(255,255,255,.55)` | Diagonal gloss overlay |
| `--blob-opacity` | `.85` | `.62` | Light-field intensity |

### 2.3 Semantic colours that need a light-theme variant

`--danger`, `--warn` and `--leave` were single values in v1.0. On light glass they measure 2.60, 2.02 and 2.95 respectively — all fail. They take the same two-value treatment as `--accent-ink`:

| Token | Dark | Light | Light measured |
|---|---|---|---|
| `--danger-ink` | `#F87171` | **`#DC2626`** | 4.54 |
| `--warn-ink` | `#F59E0B` | **`#B45309`** | 4.73 |
| `--leave-ink` | `#C4B5FF` | **`#5D46C2`** | 4.55 on the violet-26% tint |
| `--success-ink` | `#00E5C0` | **`#007764`** | 4.60 on the teal-20% tint |

`--danger` and `--warn` remain available as *fills and rules* in both themes. Only their **text and border** roles switch to the `-ink` variants on light.

### 2.4 The rule you cannot break

`#C8FF00` measures **1.11:1** against light glass — nowhere near the 4.5:1 required for text, and below the 3:1 required for meaningful borders and indicators. On light theme it must **never** set type, and must never be the only carrier of a state. Use it as a fill behind `--on-brand` text. Use `--accent-ink` wherever accent-coloured type is needed. On dark it may set type freely (14.70:1).

**Where brand is used as a non-text indicator** — balance bar fill, calendar present-day, map pin, active tab well — it is permitted at 1.11:1 **only because each instance also carries a text label**. This is §14's "colour is never the only signal" doing the work. Any new brand-coloured indicator without an accompanying label is a defect.

### 2.5 No opacity multipliers on ink tokens

**New rule.** `opacity` must never be applied to `--ink2` or `--ink3` to produce a lighter text colour. Every failure found in the mockup was produced this way — the screen eyebrow at `opacity: .6` measures 2.66:1 where the un-multiplied token measures 6.36:1.

If a lighter text value is needed, it already exists: `--ink-muted`. If a *fourth* level is needed, raise it rather than inventing one at the call site.

**One exemption exists**, recorded under §10.2 #21: the clock seconds. It is granted only because that element is decorative and `aria-hidden`, and it is void if that ever stops being true. An opacity multiplier anywhere else is a defect, not a precedent.

---

## 3. The light field

Glass requires colour behind it or it renders as grey fog. Every screen carries three blurred radial gradients beneath the UI layer.

```
blob A   230px   radial-gradient(circle, rgba(200,255,0,.72), transparent 70%)    top:-56   left:-180
blob B   210px   radial-gradient(circle, rgba(0,229,192,.62), transparent 70%)    bottom:76  right:-163
blob C   180px   radial-gradient(circle, rgba(123,92,255,.66), transparent 70%)   bottom:-42 left:-137
```
**These are box ORIGINS. §3.3 constrains the CENTRE**, which is `origin + size/2`. Reading an origin as a centre is what put all three centres inside the content column in v1.1 — see §14.4 exception 8. The horizontal values above were corrected in v1.4; sizes, colours, blur and vertical offsets are unchanged.

| Blob | Size | Origin (x) | **Centre x** | Clear of the column |
|---|---|---|---|---|
| A | 230px | `left: -180` | **−65** | 80px |
| B | 210px | `right: -163` | **448** | 73px |
| C | 180px | `left: -137` | **−47** | 62px |

```
filter: blur(36px);   opacity: var(--blob-opacity);
```

### 3.1 Static in-app — not negotiable
The drift animation in the mockup is a presentation device. Continuous animation of blurred layers behind `backdrop-filter` is the single most expensive thing this design can do to a mid-range Android. **The blobs do not move in the app.**

### 3.2 The field lives inside the page — critical
Chromium's `backdrop-filter` only filters its **own isolation group**. Any ancestor with `opacity`, `filter`, `transform`, `will-change` or `mix-blend-mode` becomes a backdrop root and the blur stops seeing through it.

Ionic's page transitions animate `transform` and `opacity` on `.ion-page`. **Therefore the light field must be rendered inside each page's stacking context, beneath the content layer — never as a global background on `ion-app` or `body`.** A global field will render correctly in dev and turn to grey fog during and after every navigation.

### 3.3 Blob placement constraint — replaces adaptive contrast
Native Liquid Glass stays legible over anything because the OS re-samples the backdrop and adjusts the foreground. CSS cannot do this. Our substitute is that we control what sits behind the glass.

**No blob centre may fall inside the content column** — and, because the gradient is ~80px wide, the centre must clear the column by more than the gradient reaches, not merely sit outside it. Measured worst case if this is violated: `--ink2` over a chartreuse blob centre on **dark** theme drops to **1.26:1**.

The required clearance is a property of each blob's radius, and is asserted numerically in `design/gates/contrast.mjs`, which reads the same tokens the CSS does: **A 80px, B 73px, C 62px**. A centre placed exactly on the column edge still fails; a 20px margin still fails. Only clearance beyond the gradient's own reach passes.

**Vertical needs no equivalent rule.** The content column is defined horizontally (`100% − 30px`) and spans the full scrollable page height, so there is no `y` at which content is absent. Once a centre clears the column on `x`, the nearest content point sits on the same horizontal line and the worst case is fixed regardless of `y`; moving a blob vertically off-screen can only increase the distance, never decrease it.

Any new screen that introduces a fourth blob, moves a centre inward, or raises `--blob-opacity` is a spec change, not a screen decision.

---

## 4. Typography

### 4.1 Stack
```
--display: -apple-system, BlinkMacSystemFont, 'Inter Tight', 'Inter', 'Segoe UI', Roboto, sans-serif
--ui:      -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif
--mono:    'SF Mono', 'JetBrains Mono', ui-monospace, 'Cascadia Mono', monospace
```

**Do not bundle SF Pro.** Apple licenses it for Apple platforms only. Leading with `-apple-system` gives genuine SF Pro on iOS/macOS at no cost, Roboto on Android, Inter elsewhere.

**Self-host Inter, Inter Tight and JetBrains Mono** as WOFF2, subset to Latin, `font-display: swap`. Do not load from a CDN — the current app loads Archivo from Google Fonts and that link is removed by this work. `@fontsource-variable/inter` and `@fontsource-variable/inter-tight` are the intended packages. Note that frappe-ui already bundles Inter variable; confirm which copy wins before adding a second.

Mono is **in-app**, not documentation-only: pro-rated notes, geo coordinates, ticket IDs, the OT eligibility hint, the KPI cycle pill.

### 4.2 Scale

**Floor raised to 10px.** v1.0 specified 7.5px and 8.5px. Those sizes fail at arm's length on a 390px screen under warehouse fluorescents, and the app's most-used screen is operated outdoors. The visual change is small; the legibility change is not.

| Role | Family | Size | Weight | Tracking | Line | Example |
|---|---|---|---|---|---|---|
| Clock | display | 36px | 800 | −0.02em | 1.0 | Check-in time |
| Display number | display | 31px | 800 | **−0.02em** | 1.0 | Balance "7.5" |
| Ring centre | display | 25px | 800 | −0.02em | 1.0 | KPI "4.2" |
| Stat number | display | 22px | 800 | −0.02em | 1.0 | "10 PRESENT" |
| Screen title | display | 21.5px | 800 | −0.025em | 1.15 | "My KPI" |
| Button label | display | 15.5px | 800 | −0.01em | 1.2 | "CHECK IN" |
| Panel title | display | 14.5px | 800 | −0.02em | 1.2 | "August 2026" |
| Row label | ui | 12.5px | 500 | 0 | 1.4 | "Apply for leave" |
| Card title | ui | 12.5px | 600 | 0 | 1.4 | "Leave balance looks wrong" |
| KRA label | ui | 11.5px | 600 | 0 | 1.4 | "Data accuracy" |
| Eyebrow | ui | **10.5px** | 600 | 0.13em | 1.3 | "H1 2026 REVIEW" — **no opacity** |
| Caption | ui | 10.5px | 400 | 0.02em | 1.45 | "Last check-out 6:17 pm" |
| Field label | ui | **10px** | 600 | 0.14em | 1.3 | "DATE WORKED" — was 8.5px |
| Micro label | ui | **10px** | 600 | 0.13em | 1.3 | "ANNUAL LEAVE" — was 8.5px |
| Badge | ui | **10px** | 700 | 0.09em | 1.2 | "OPEN" — was 7.5px |
| Tab label | ui | **10px** | 600 | 0.07em | 1.2 | "HOME" — was 8.5px |
| Data / system | mono | **10px** | 400 | 0 | 1.5 | Coordinates, ticket IDs — was 8–9px |

Tracking on the raised sizes is reduced proportionally so the labels occupy roughly their original width. Verify the tab bar and the 4-up balance grid at 390px before sign-off; if a label wraps, shorten the string rather than lowering the size.

**The scale is closed.** Where a component entry in §10 names a size not in this table, the nearest scale step governs and the component entry is corrected. Sizes 13px, 15px, 23px and 10.5px appearing in §10.2 #16, #21, #23 and #18 are superseded by their nearest steps.

Applied, with the resolved sizes now written into those four entries:

| Entry | Named | Nearest step | Resolved |
|---|---|---|---|
| §10.2 #16 KRA score | 13px | Card title | **12.5px** |
| §10.2 #21 Clock seconds | 15px | Button label | **15.5px** |
| §10.2 #23 Logo well | 23px | Stat number | **22px** |
| §10.2 #18 Calendar day | 10.5px | Caption | **10.5px** — already a step; the entry now names the token |

This ruling governs **size only**. Weights, tracking and family stated in a §10 entry stand as written: a 12.5px numeral at weight 800 is the Card title *step* carrying the entry's own weight, not a new step.

### 4.3 Tabular figures — mandatory
Every number in this app is data. `font-variant-numeric: tabular-nums` on all balances, times, scores, currency, calendar digits and IDs.

---

## 5. Spacing, radius, layout

| Token | Value | Applies to |
|---|---|---|
| `screen-gutter` | 15px | Left/right padding of all screen content |
| `stack-sm` | 9px | Between sibling cards in a grid |
| `stack-md` | 13px | Between major blocks |
| `stack-lg` | 16px | Below the screen title |
| `pad-panel` | 14px 13px | Balance cards, stat tiles |
| `pad-row` | **11.5px 15px** | List rows *(was 12px 15px)* |
| `pad-action` | **17px 18px** | Primary and ghost buttons *(was 16px 18px)* |
| `pad-badge` | **3.5px 8px** | Badges *(was 4px 8px)* |
| `radius-panel` | 20px | Glass panels, list containers |
| `radius-action` | 19px | Buttons, map panel, selfie panel |
| `radius-card` | 17px | Balance cards, goals panel |
| `radius-banner` | 16px | Banners, issue cards |
| `radius-tile` | 15px | Stat tiles |
| `radius-input` | 14px | Form fields |
| `radius-well` | 9px | Icon wells |
| `radius-pill` | 6px | Badges, pills |
| `radius-tabbar` | 22px | Bottom navigation |

**Reference viewport** 390 × 844 CSS px. Content column is `100% − 30px`. Tab bar pinned above the safe area with a 9px gap beneath. All screens scroll; the tab bar never scrolls.

**Minimum touch target** 44 × 44 px. Where a visual element is smaller — chevrons, calendar days, tab items — the tappable area is padded out to 44px without moving the visual.

---

## 6. The glass recipe

```css
background: var(--glass-fill);
backdrop-filter: blur(var(--blur-panel)) saturate(180%);
-webkit-backdrop-filter: blur(var(--blur-panel)) saturate(180%);
border: 1px solid var(--glass-rim);
border-radius: var(--radius-panel);
box-shadow:
  inset 0  1px 0 var(--rim-hi),
  inset 0 -1px 0 var(--rim-lo),
  var(--lift);

/* diagonal gloss, ::after, pointer-events: none */
background: linear-gradient(155deg, var(--sheen), transparent 40%);
```

**Two blur values, both correct:**
- `--blur-panel: 20px` — all glass panels
- `--blur-ghost: 18px` — the ghost action only

v1.0 said "one class, do not create variants" while the mockup uses 18px on the ghost button. The mockup governs; the variant is named rather than accidental.

**Light glass is more opaque than dark glass** — 56% against 7.5%. Below roughly 50% on light, the field bleeds through and legibility collapses. Do not "correct" this.

### 6.1 Fallback
Where `backdrop-filter` is unsupported, panels fall back to a solid fill at the same lightness: `#15171D` on dark, `#FFFFFF` at 92% on light. **The layout must not change.** Detect with `@supports not (backdrop-filter: blur(1px))`.

### 6.2 Reduce-transparency mode — new, required
A user setting and a media query that swap `--glass-fill` to the §6.1 fallback values across the app. It reuses the fallback tokens, so it costs almost nothing.

- Honours `prefers-reduced-transparency`
- Exposed as an explicit toggle in app settings, persisted alongside the theme preference
- **No layout change**, only fill values

Apple shipped Liquid Glass without an adequate version of this, added one under pressure, then changed its defaults. We ship it from the start.

### 6.3 Where glass must stop
Performance ratings, payslip figures and leave balances sit on the most opaque available surface in both themes. The KPI ring track, the KRA bars and payslip line items use solid values, never translucency. **A number a person may dispute with their manager must not be read through a moving tint.** Do not apply glass to these for visual consistency.

**This section overrides the component entries in §10 where they conflict.** Those entries describe the visual; they do not grant an exemption. The token is **`--track-solid`** (`#ECEDEF` light / `#313133` dark — the exact composite of `--icon-bg` over glass, so the appearance is unchanged while the value stops shifting with whatever sits behind it). It backs the KPI ring track (§10.1 #9), the balance bar track (§10.1 #6) and the KRA bars (§10.2 #16). `--icon-bg` remains correct for icon wells, which carry no number.

---

## 7. Presentation material vs app material — new

The mockup is a pitch document. Four of its effects belong to the document and must not ship.

| Effect | Ships? | Reason |
|---|---|---|
| Drifting blobs (34–46s infinite) | **No** | Per-frame recomposition of every glass layer above |
| **Film grain overlay** (`mix-blend-mode`, full viewport) | **No** | `mix-blend-mode` on a full-viewport layer **creates a backdrop root** and would disable every `backdrop-filter` beneath it. If texture is wanted, bake it into the field layer *below* the glass as a static image — never as a blend-mode overlay above it |
| **Cursor-following light** | **No** | No pointer on a phone |
| **Shimmer sweep on the primary action** | **No** | It animates `left`, triggering layout every frame — a direct violation of §15. A 4.2-second infinite shimmer on the button people press twelve times a day is motion carrying no information |

**General rule:** anything in the mockup that moves without being caused by a user action is presentation material until this document says otherwise.

---

## 8. Motion

| Interaction | Duration / easing | Property |
|---|---|---|
| Button press | 120ms `cubic-bezier(.2,.8,.3,1)` | `transform` + `box-shadow` |
| Row tap | 90ms ease-out | background → `--icon-bg` |
| Screen push | 280ms `cubic-bezier(.32,.72,0,1)` | `transform: translateX` |
| Sheet present | 340ms `cubic-bezier(.32,.72,0,1)` | `transform: translateY` |
| Theme change | 400ms ease | `background-color`, `color`, `border-color` only |
| Skeleton shimmer | 1400ms linear infinite | `transform: translateX` |
| Check-in success | 420ms one-shot | `scale` 1 → 1.04 → 1 |

**Never animate** the size, position or blur radius of any element carrying `backdrop-filter`. Animate only `transform` and `opacity`.

**Theme transition scope:** apply the 400ms transition to a wrapper, not to every node. Transitioning colour across the whole tree while `backdrop-filter` recomposites is expensive. The existing View Transitions circular reveal in `data/theme.js` is retained and is preferred where supported.

All motion suppressed under `prefers-reduced-motion: reduce`, including the skeleton shimmer, which becomes a static fill.

---

## 9. Icons

Stroke-based line icons on a 16 × 16 grid, inline SVG so they inherit theme colour. No icon fonts, no raster assets.

| Property | Value |
|---|---|
| Grid | 16 × 16 viewBox (24 × 24 for the selfie face only) |
| Rendered size | 14 × 14 px inside a 27 × 27 well |
| Stroke width | 1.55 |
| Caps / joins | round / round |
| Fill | none |
| Colour | `currentColor` at 0.85 opacity |

**Note on crispness:** 1.55 stroke on a 16-grid rendered at 14px yields a ~1.36px stroke. Verify at 2× and 3× density; if it renders soft, adjust the grid rather than the stroke so the whole set stays consistent.

No public icon set matches this grid and weight. The 9 existing hand-drawn icons are retained and extended. Additional icons are drawn on the same grid at the same weight and **submitted for approval before use**.

---

## 10. Components

28 components. Each is built with **all applicable states**: default, pressed, disabled, pending, focus, error, empty, loading. Each is entered in the `/design` specimen route (§16.4) in both themes.

### 10.1 Core — specified in v1.0, corrected here

| # | Component | Key values | Change from v1.0 |
|---|---|---|---|
| 1 | **Primary action** | `pad-action` 17px 18px, `radius-action` 19px, `linear-gradient(135deg,--brand,--brand-2)`, text `--on-brand`, shadow `0 10px 30px rgba(200,255,0,.34)` + `inset 0 1px 0 rgba(255,255,255,.6)` + `inset 0 -2px 0 rgba(0,0,0,.14)` | Padding; **pending state added**; sweep removed |
| 2 | **Ghost action** | Glass at `--blur-ghost` 18px, `--ink` label | Blur named |
| 3 | **List row** | `pad-row` 11.5px 15px, gap 11px, well 27×27 r9, label 12.5/500, chevron `--ink3`, divider 1px `--hair` inset 15px each side, first row exempt, min-height 44px | Padding |
| 4 | **Input field** | `pad` 13px 14px, `radius-input` 14px, 12.5px, placeholder `--ink-muted`, filled `--ink` | Placeholder token; focus ring redesigned |
| 5 | **Textarea** | Input variant, height 66px, `align-items: flex-start` | Newly specified |
| 6 | **Balance card** | `pad-panel` 14px 13px, `radius-card` 17px, number display 31/800/−0.02em tabular, label 10px/600/0.13em, bar 3px track **`--track-solid` — solid per §6.3, which governs here: the bar reads a leave balance** fill `--brand` + glow | Tracking; label size; **track solid (§6.3)** |
| 7 | **Badge** | 10px/700/0.09em, `pad-badge` 3.5px 8px, `radius-pill` 6px. OPEN: light `--brand` on `--on-brand`, dark brand-18% tint. RESOLVED: light `--success-ink` on teal-20%, dark `--success` | Size; resolved ink |
| 8 | **Tab bar** | Glass, `radius-tabbar` 22px, pad 11px 6px 9px, label 10px/600/0.07em, well 19×19 r7, active well `--brand` + glow, pinned above safe area | Label size; five fixed items |
| 9 | **Progress ring** | 88×88, r38, stroke 7, round cap, circumference 238.8, `dashoffset = 238.8 × (1 − score/max)`, track **`--track-solid` — solid per §6.3, which governs here**, arc `--brand`, centre display 25/800 | **Track solid (§6.3)** |
| 10 | **Banner** | Glass, `radius-banner` 16px, pad 13px 14px, left rule 3px full height — info `--brand`, warning `--warn`, error `--danger` | Radius named |
| 11 | **Empty state** | 1px **dashed** `--glass-rim`, pad 26px 18px, centred, title display 13.5/700, body 11px `--ink2` | Unchanged |
| 12 | **Skeleton** | Mirrors the real layout — same panel, same radii, same block sizes. Block `--icon-bg` r6. Shimmer `translateX` 1400ms. **No spinners anywhere in this app** | Unchanged |

### 10.2 From the mockup — newly specified

| # | Component | Notes |
|---|---|---|
| 13 | **Stat tile** | 3-up grid, `radius-tile` 15px, pad 12px 6px, number display 22/800, label 10px/600/0.11em. **Flattened** — see §15.2 |
| 14 | **Issue card** | `radius-banner` 16px, pad 13px, mono ID row + badge, title 12.5/600, meta 10px `--ink2` |
| 15 | **Score panel** | Ring + verdict + cycle pill, pad 17px 15px, `radius-panel` 20px |
| 16 | **KRA panel** | Rows pad 11px 0, divider `--hair`, label 11.5/600 + mono weight, score display **12.5/800** *(Card title step — §4.2)*, bar 4px on a **`--track-solid`** track *(§6.3 names KRA bars)* |
| 17 | **Goals panel** | `radius-card` 17px, numeral display 22/800 `--accent-ink`, chevron |
| 18 | **Calendar** | `radius-action` 19px, pad 15px 13px, 7-col grid gap 4px, day **10.5px Caption step** r8. Present: light solid `--brand` + `--on-brand`, dark brand-19% tint. On leave: `--leave-ink` on leave-26%. Rest day: `--ink3` — **no opacity multiplier**. Legend swatches 7×7 r2.5 with text labels |
| 19 | **Map panel** | 150px, `radius-action` 19px, themed gradient + perspective grid, pin `--brand` with rings, geo caption mono 10px in a glass chip |
| 20 | **Selfie panel** | 118px, `radius-action` 19px, 48px dashed `--accent-ink` ring, 24×24 face icon |
| 21 | **Clock** | Display 36/800/−0.02em, seconds at **15.5px**/600 *(Button label step — §4.2)* opacity .55 — **decorative, not information**. §2.5 exemption recorded below the table |
| 22 | **Note panel** | Eligibility hint — glass, `radius-input` 14px, pad 12px 14px, mono 10px `--accent-ink` |
| 23 | **Logo well** | 56×56, `radius-action` 19px, glass, display **22px** *(Stat number step — §4.2)* `--accent-ink` |

**§2.5 exemption — clock seconds (#21), the only one granted.** The seconds carry `opacity: .55`, which §2.5 otherwise forbids. It stands because the seconds are **decorative and `aria-hidden`**, and because the multiplier sits on `--ink`, not on `--ink2` or `--ink3`, which is what §2.5's letter names. Measured over glass the result is **4.26:1 on light** (6.03 dark) — below the 4.5 §14.1 requires of body text, and at 15.5px/600 they do not qualify as large text either.

**The exemption is void the moment the element stops being decorative.** If the seconds are ever announced, relied on, or read as information, this becomes the same defect §14.4 exception 1 removed from the screen eyebrow, and the opacity comes off.

### 10.3 Required by the app, absent from the mockup

These exist in `nz-version-16` and will be rendered by this system whether or not they are specified. Specifying them is the difference between a coherent app and a coherent demo.

| # | Component | Existing file |
|---|---|---|
| 24 | **App header** — title, notification bell + unread dot, avatar | `BaseLayout.vue` |
| 25 | **Modal / bottom sheet** | `CustomIonModal.vue` — **retain the focus-trap workaround**, reskin via CSS vars only |
| 26 | **Action sheet** | `RequestActionSheet`, `WorkflowActionSheet`, `ListFiltersActionSheet` |
| 27 | **Toast** | frappe-ui `Toasts` |
| 28 | **Workflow status chip** | **The state set is open, not the five states earlier drafts named** — see below the table |

**#28 Workflow status chip — the real state set.** Earlier drafts of this row named five states (Draft / Submitted / Approved / Rejected / Cancelled). That was a guess made before the shipped code was read, and the data disagrees: the app's `chipMap`s carry **composite** states, and Frappe workflows are user-configurable, so **any closed list is wrong by construction**.

Sixteen known states map onto **six variants**. An unknown state renders `neutral` rather than failing — a chip that refuses to render is worse than one that renders grey.

| Variant | States | Treatment | Measured light / dark |
|---|---|---|---|
| `neutral` | Draft, *and any unknown state* | `--ink2` on `--icon-bg` | 5.75 / 5.85 |
| `attention` | Open, Pending, Unpaid | `--warn-ink` on glass, 1px `--warn` outline | 4.72 / 8.12 |
| `progress` | Submitted, Approved & Draft, Approved & Unpaid, Approved & Submitted, On leave | `--accent-ink` on brand-14% | 7.02 / 10.16 |
| `success` | Approved, Paid, Present | `--success-ink` on success-20% | 4.60 / 6.88 |
| `danger` | Rejected, Absent | `--on-brand` on **solid** `--danger` | 7.11 / 7.11 |
| `muted` | Cancelled | `--ink-muted` on glass, 1px `--hair` outline | 4.56 / 4.58 |

Two treatments are outlines rather than tints because the tint fails §14: `warn-ink` on a warn tint measures **4.27** on light, and a danger tint cannot clear 4.5 on light at any usable alpha — hence the solid danger fill.

The status word is always rendered, so colour is never the only signal (§14.1).

**Label chips are not status chips.** A grade, a category, a count or a department is a label; it belongs in `GBadge` (`accent` / `neutral` variants), not in the status chip. Mixing them is how "Cancelled" ended up rendering as a bright brand chip in the Modernist code this replaced.

**Also requiring a treatment, inheriting from the above:** link/autocomplete picker, date picker, file upload and preview, avatar, segmented control (`TabButtons`), data tables (payslip, expenses — **solid per §6.3**), pull-to-refresh, search/filter bar, side nav **[DECISION 1]**, error surface (`ResourceError`, 21 usages), the three geofence dialogs, PDF viewer, push-notification prompt.

---

## 11. States not in the mockup

The mockup shows populated happy paths only. These states are built to this section. They are the difference between a demo and a product.

### 11.1 Empty
An empty screen is an invitation to act. Always say what to do; never "no records found".

| Screen | Title | Body |
|---|---|---|
| Overtime history | No overtime claims yet | Stay past your shift end, punch out, and claim it here |
| Leave history | No leave taken this year | Your applications will appear here once submitted |
| Issues | Nothing reported | If something looks wrong, tell us — a screenshot helps |
| Balances | No leave allocated yet | People & Culture are setting this up. Check back shortly. |
| Payslips | No payslips available | Your first payslip appears after your first full pay cycle |
| KPI | No review cycle open | Your next appraisal will appear here when it starts |
| SOPs | No documents yet | Procedures for your role will appear here |
| Team requests | Nothing waiting on you | Approvals will appear here when your team submits |

### 11.2 Loading
Skeleton mirrors the real layout. No spinners. Static fill under reduced motion. **The 7 existing `LoadingIndicator` usages are replaced.**

### 11.3 Error and offline

| Condition | Message | Action |
|---|---|---|
| No network | You are offline. Your last check-in was saved. | Retry — persistent banner, warning rule |
| Location denied | Turn on location to check in. Settings → Privacy → Location. | Open settings |
| Camera denied | Turn on camera access to take your check-in photo. | Open settings |
| Punch failed to save | Check-in did not save. Tap to try again — do not punch twice. | Retry, error rule |
| Outside shift window | Your shift window opens at 8:30 am. | Informational |
| Insufficient balance | You have 2.5 days available and applied for 3. | Inline field error |
| Past OT cutoff | The pay cutoff for this date has passed. You can still claim it as replacement leave. | Route to replacement leave |
| Outside geofence | You are not at a registered location. Check in remotely and it goes to your manager. | Route to remote check-in |
| Server error | Something went wrong on our side. Try again in a moment. | Retry |

**Message rules.** Errors state what happened and what to do. They never apologise, never blame the user, and never surface a system term — no doctype names, no permission errors, no stack traces. If a message cannot be written in plain language, the interaction needs redesigning rather than rewording.

### 11.4 Pending — new, and distinct from disabled

v1.0 used **disabled** for two different meanings: "you cannot do this" and "your tap registered, waiting on the server". They must look different, because the second is feedback and the first is not — and disabled measures 2.68:1, so it reads as nothing happening.

| State | Treatment | Announced |
|---|---|---|
| **Disabled** | `--icon-bg` fill, `--ink3` label, no shadow, `cursor: not-allowed` | `aria-disabled="true"` |
| **Pending** | **Keeps the brand fill.** Label swaps to the progressive form — "Sending…", "Checking in…". A 2px indeterminate bar along the bottom edge, `transform`-animated | `aria-busy="true"` |

Pending is not a spinner and does not violate §11.2.

### 11.5 Duplicate submission guard
A second submission of the same action within **60 seconds** is rejected client-side. The primary action enters **pending** on first tap and stays there until the server responds. This is not cosmetic: the current app has produced up to nine identical check-in records from one user in the same second.

---

## 12. Screen anatomy

Stack order top to bottom. Vertical gap is `stack-md` (13px) unless stated. All screens: 15px gutters, tab bar pinned.

**These anatomies were transcribed from the mockup and diverge from the shipped app in both directions** — the mockup drew things the app does not have, and the app has things the mockup never showed. Where they differ:

- **the app governs SCOPE.** An element the mockup drew but the app does not have is a feature request, not a defect, and §1 puts features out of scope. It goes to `docs/glass/decisions/` as a candidate.
- **the anatomy governs LAYOUT of what exists** — order, spacing, which primitive.

Home is the worked example (v1.5): the mockup's balance grid was removed because the shipped screen has no balance data and no call to fetch it, and the request panel was added because the screen has one. **Check every anatomy against the actual screen before building it.**

| Screen | Stack | Primary action |
|---|---|---|
| **Sign in** | Logo well (56×56, r19) → title → subtitle → email field → password field → primary → forgot-password link. Vertically centred, 40px bottom offset | SIGN IN |
| **Home** | Status → eyebrow date + greeting → last-punch caption → *banner if unresolved punch* → primary → quick-link list (4 rows) → **request panel** → tab bar | CHECK IN / CHECK OUT |
| **Check in** | *A bottom sheet, not a route — see the note below the table.* Eyebrow (the action label) → clock (36px) → date line → location status + distance → map panel (150px) → selfie panel (live preview) → primary | CONFIRM CHECK IN |
| **Leave** | Eyebrow + title → balance panel (**N types, one surface**) → replacement-leave card → primary → RECENT field label → history list → holidays → tab bar | REQUEST A LEAVE |
| **Attendance** | Eyebrow + title → calendar panel → stat panel (**4-up**, one surface) → primary → action list (3 rows, one surface) → request lists → tab bar | REQUEST ATTENDANCE |
| **Overtime** | Eyebrow + title → date field → hours field → eligibility note panel → explanation field (66px) → primary → routing caption → tab bar | SEND TO APPROVER |
| **KPI** | Eyebrow + title → score panel (ring + verdict + pill) → KRA field label → KRA panel (4 rows) → goals panel → tab bar | none — read-only |
| **Issues** | Eyebrow + title → stat panel (3-up, **one surface**) → issue cards → primary → screenshot hint caption → tab bar | REPORT AN ISSUE |

**Leave diverges** (reconciled in v1.6, batch 3):

| Anatomy said | The app has | Resolved |
|---|---|---|
| Balance panel 2×2 — four cards | **N cards**, one per allocated leave type; an employee may have two or five | **App.** `GBalanceGrid` is one surface at any count, so §15.2's flattening holds unchanged |
| — | A **pro-rated headroom band** and per-card qualifiers ("Pro-rated: 8 allocated for 2026", "incl. carry-forward") | **App.** `GBalanceCard` gained a `note` slot, and an `entitlement` prop: the gauge measures against the annual entitlement while the announcement says what was actually allocated |
| — | A replacement-leave card and a holidays panel the anatomy omits | **App** |
| §11.3 inline insufficient-balance error | No client-side balance validation at all | **App** — adding it is new validation, filed as a candidate in `docs/glass/decisions/` |

**Attendance diverges too** (reconciled in v1.6, batch 2):

| Anatomy said | The app has | Resolved |
|---|---|---|
| Stat panel 3-up | Four statuses — Present, Half Day, Absent, On Leave | **App** — `GStatPanel` takes a `columns` prop |
| One ghost action | Four actions, and three request lists the anatomy omits | **App** — but the three secondary actions were three glass surfaces, putting the screen at 7 of 6, so §15.2 flattening applies: one panel, three rows |
| — | A **Half Day** calendar state the mockup never drew | **App** — `GCalendar` gains a `half` state, `--accent-ink` on brand-26%, measured 6.88 / 6.87 |

**Check in is a sheet, not a screen** (reconciled in v1.5, batch 2). It presents from Home's primary action, so it has no tab bar and overlays the Home surfaces rather than replacing them. Four further divergences, all resolved under v1.5's rule:

| Anatomy said | The app has | Resolved |
|---|---|---|
| Eyebrow = location name | Eyebrow = the action label; location status sits below the clock with the distance readout | **App** — the location is live status, not a title |
| Map panel 150px | 200px | **Anatomy** — now 150px via `GMapPanel` |
| Selfie panel 118px | A live 4:3 camera preview | **App** — 118px sizes the mockup's static placeholder; a face framed at 118px is not a usable preview. 118px is now a floor, not a fixed height |
| Shift status caption | A date line under the clock | **App** — no shift caption exists to style |

**Screens not in the mockup**, inheriting these patterns: Expenses, Employee Advance, Shift Request, Shift Assignment, Salary Slip, SOP list/detail, Team dashboard, Remote approvals, HR contacts, More, Notifications, Profile, App settings, Change password, Forgot password, Invalid employee. Each is built from §10 components with no new primitives. Any screen that appears to need a new primitive raises it against this document instead of inventing one.

---

## 13. Navigation

### 13.1 Tab bar — five fixed destinations **[DECISION 2]**

The mockup shows `HOME · ATTEND · LEAVE · PAY · ISSUES` on five screens and swaps the fifth slot to `KPI` on the KPI screen — six destinations in five slots. The app currently has eight. A tab bar whose destinations change under the user is disorienting and breaks Ionic's per-tab navigation stacks.

**Recommended:** `HOME · ATTEND · LEAVE · PAY · MORE`, with KPI, Issues, SOPs, Expenses, Team and Remote Approvals behind More. It is the only arrangement that survives the app growing again.

### 13.2 Safe area — existing bug
The shipped viewport meta is:
```
width=device-width, initial-scale=1.0, viewport-fit=cover maximum-scale=1.0, user-scalable=no
```
`viewport-fit=cover` and `maximum-scale=1.0` are **space-separated where the directive list must be comma-separated**. `viewport-fit=cover` is what makes `env(safe-area-inset-*)` return non-zero on iOS. Fix the separator, and remove `user-scalable=no` — it blocks user zoom, which fails §14.

Note the interaction: removing `maximum-scale=1` restores iOS focus-zoom on inputs below 16px. Accept it, or raise input font-size. **[DECISION 3]**

### 13.3 Desktop **[DECISION 1 — resolved: in scope]**
`SideNav.vue` exists (72px collapsed / 216px expanded at `lg:`), and the tab bar is `lg:hidden`. v1.0 declared desktop out of scope. Either Glass covers `lg:` in this phase, or the app ships two visual identities on one codebase.

**Resolved: desktop is in scope.** HR admin and managers use the desktop view regularly. §20 governs the `lg:` layout; there is no desktop mockup, so §20 holds the role the mockup holds for mobile. Component contracts in §10 state `lg:` behaviour where it differs — the list is §20.7, and the default is "identical at both breakpoints".

---

## 14. Accessibility — acceptance criteria

### 14.1 Criteria
- **Body text** 4.5:1 minimum, measured against the **brightest point of the light field**, not the flat background
- **Large text and UI** 3:1 minimum — text above 18.66px bold, icons, component borders, state indicators
- **Chartreuse never sets type on light.** `#C8FF00` on light glass is 1.11:1
- **No opacity multipliers on ink tokens** (§2.5)
- **Touch targets** 44 × 44 px including chevrons, calendar days, tab items, dismiss controls
- **Focus visible** — see 14.3. Never `outline: none` without a replacement
- **Reduced motion** — all animation suppressed, including skeleton shimmer and the check-in pulse
- **Reduced transparency** — §6.2
- **Colour is never the only signal** — attendance states carry a text label; badges carry words
- **Screen reader labels** — every icon-only control has an accessible name. Balance cards announce as "Annual leave, 7.5 days remaining of 8 allocated"
- **Dynamic type** — layout survives 120% scaling without clipping. Test Home and KPI specifically
- **Theme follows system by default**, with a persisting in-app override

### 14.2 Verified token pairs

| Pair | Light | Dark |
|---|---|---|
| `--ink` on glass | 18.40 | 17.38 |
| `--ink2` on glass | 6.36 | 7.79 |
| `--ink2` over blob edge | 6.23 | see 14.4 |
| `--ink-muted` on glass | **4.56** | **4.56** |
| `--ink3` on glass (non-text) | **3.07** | 3.59 |
| `--accent-ink` on glass | 7.21 | 14.70 |
| `--on-brand` on `--brand` | 16.63 | 16.63 |
| `--danger-ink` on glass | **4.54** | 6.28 |
| `--warn-ink` on glass | **4.73** | — |
| `--leave-ink` on leave tint | **4.55** | — |
| `--success-ink` on teal tint | **4.60** | 10.73 |

### 14.3 Focus ring — redesigned
v1.0 specified a 3px `#C8FF00` ring. On light glass that measures **1.11:1** against a 3:1 requirement — the spec's own §2.4 forbids it.

```
/* both themes */
box-shadow:
  0 0 0 2px var(--ink),     /* inner — 18.4:1 light, 17.4:1 dark */
  0 0 0 5px var(--brand);   /* outer — brand identity, contrast carried by the inner ring */
```
The inner ring carries the contrast; the outer ring carries the brand. Applied to every interactive element on `:focus-visible`.

### 14.4 Recorded exceptions
The mockup governs values except where it fails a criterion above. Eight exceptions, all resolved in favour of §14:

1. Screen eyebrow `opacity: .6` → removed (2.66 → 6.36)
2. Calendar rest days `opacity: .45` → removed (1.55 → 3.07 as non-text; day numbers use `--ink-muted`)
3. Ticket IDs 8px `--ink3` → 10px `--ink-muted` (2.96 → 4.56)
4. Calendar on-leave violet → `--leave-ink` (2.95 → 4.55)
5. Badge RESOLVED `#00806B` → `--success-ink` `#007764` (4.09 → 4.60)
6. Type sizes 7.5 / 8.5px → 10px floor
7. Focus ring → two-tone (1.11 → 18.40 on the inner ring)
8. **Light-field blob origins → moved outward (v1.4).** §3's coordinates were read as centres when they are box origins, putting all three centres inside the content column and violating §3.3 in the same document. The conflict rule applies: the mockup governs values except where a criterion in §14 fails, and these coordinates failed it. Measured over glass on the reference viewport, worst case per blob:

   | | Before | After | Threshold |
   |---|---|---|---|
   | `--ink2` dark over blob A | **1.26** | **7.75** | 4.5 |
   | `--ink-muted` dark over blob B | **1.18** | **4.55** | 4.5 |
   | `--ink2` dark over blob C | **3.44** | **7.75** | 4.5 |
   | `--ink-muted` light over blob C | **3.71** | **4.55** | 4.5 |

   Fixed by geometry alone — `--blob-opacity` and `--glass-fill` are unchanged. All 12 blob pairs now pass; the gate holds 30/30. **The field's placement now differs visibly from the mockup**: the blobs read as three corner glows rather than visible cores, because a core bright enough to see is a core too bright to read text over. This is on the device-review list.

**Standing risk, dark theme:** `--ink2` over a chartreuse blob **centre** measures 1.26:1. This is why §3.3 is a hard constraint rather than guidance. There is no token fix; the fix is placement.

---

## 15. Performance budget

This design uses `backdrop-filter`, which is GPU-expensive. These limits are not suggestions — the primary users are on mid-range Android on 4G, frequently outdoors.

| Constraint | Limit | Why |
|---|---|---|
| Glass surfaces per screen | **6** | Each is a separate compositing layer |
| Blur radius | 20px panel / 18px ghost | Cost scales with radius; 40px is ~4× the cost of 20px |
| Light-field blobs | 3 per screen, **static** | Animation forces per-frame recomposition of every glass layer above |
| Animated properties | `transform`, `opacity` only | Everything else triggers layout or paint |
| Nested glass | Not permitted | Doubles blur cost for no visual gain |
| `mix-blend-mode` above glass | Not permitted | Creates a backdrop root; disables the blur beneath |
| Frame rate | 60fps sustained while scrolling | Test on the lowest-spec device in the fleet **[DECISION 4 — name the model]** |
| Theme switch | No layout shift, no reflow | Only colour properties transition |

### 15.1 Counting rule
A glass container and its child rows count as **one** surface. A grid of N glass cards counts as **N**.

**Count only what composites (v1.6).** A closed sheet or modal renders nothing and costs nothing, so its contents are **not** part of the screen's count. They form their own surface set, asserted against the same limit of 6 **while presented**. A screen that owns a sheet is not charged for it.

The reason is practical: the Check-in sheet adds two surfaces to Home, which read 5 of 6 on a screen that shows three. Charging screens for sheets they are not showing inflates every screen that owns one, and would eventually block a build that is nowhere near the compositing limit. `design/gates/surfaces.mjs` implements both counts and fails on either.

### 15.2 Flattening — required
Counted as the mockup draws them, three screens sit at exactly 6 before any state is added — and §11 requires banner, empty, loading, error and offline states on top of the happy path.

| Screen | As drawn | After flattening |
|---|---|---|
| Leave | 4 balance cards + rows + tabs = **6** | 1 balance panel + rows + tabs = **3** |
| Attendance | calendar + 3 tiles + ghost + tabs = **6** | calendar + 1 stat panel + ghost + tabs = **4** |
| Issues | 3 tiles + 2 issue cards + tabs = **6** | 1 stat panel + 2 issue cards + tabs = **4** |

The 2×2 balance grid and the 3-up stat row become **one glass panel with internal dividers** at `--hair`. Card padding, radii and internal metrics are unchanged; only the surface count changes. This restores headroom for the states §11 requires.

### 15.3 Chrome is counted separately

The counts above are **per-screen content**. App chrome is counted separately, so a screen's content budget is not silently spent before its first panel exists.

| Chrome | Glass surface? | Counted where |
|---|---|---|
| **Tab bar** (§10.1 #8) | **Yes** — glass, `radius-tabbar` 22px | Counted, as the §15.2 rows show ("… + tabs") |
| **App header** (§10.3 #24) | **No** | Not a surface, so nothing to count |
| **Side nav** at `lg:` (§20.2) | Yes | Replaces the tab bar's surface — net zero |

**The app header is not a glass surface.** It sits above scrolling content, and glass above glass is nested glass, which §15 forbids outright. It takes an opaque `--bg` fill with a `--hair` bottom rule. This is also why §15.2's arithmetic never names a header: there was never one to count.

A screen therefore spends **one** of its six on chrome — the tab bar below `lg:`, the side nav above it — never two.

---

## 16. Implementation notes

### 16.1 Baseline
`Nastyworldwide-Dev/hrms@nz-version-16` — Vue 3.5, `@ionic/vue` 7.4 (`mode: "ios"`), `frappe-ui` 0.1.105, Tailwind 3.4, Vite 5, `vite-plugin-pwa`. 103 `.vue` files, 41 views, ~51 components.

**An existing token system ships on this branch** — Modernist: `--m-*` RGB triplets, semantic Tailwind colours, 14 `.m-*` primitives, a persisted light/dark/system theme store with a View Transitions reveal, and Ionic tab-bar shadow-DOM theming. Glass replaces its *values and primitives*; it reuses its *mechanism*.

### 16.2 Tokens
- One source of truth: `tokens.json`, compiled to `glass.css` (CSS custom properties), the Tailwind theme, and `theme/variables.css` (Ionic `--ion-*`). **The current three-way manual palette sync is retired.**
- Switched by `data-theme` on the root element. No duplicated stylesheets, no second component set, no theme prop threaded through components.
- `darkMode: ['selector', '[data-theme="dark"]']` — note this is also what `frappe-ui` ≥ 0.1.2xx expects.
- Tailwind tokens are **semantic** — `bg-glass`, `text-ink-2`, `rounded-panel`. A hardcoded `bg-white/[0.075]` cannot be re-themed later.
- **`borderRadius` is currently zeroed** in `tailwind.config.js` for the Modernist look. **Measured in phase 3.1** (`docs/glass/phase3-inventory.md`): `rounded-*` appears in **4 app files, 6 usages** — not the ~103 files earlier drafts of this section assumed. The real exposure is **106 utilities across 47 `frappe-ui` component files**, which sit inside the Tailwind content glob; 17 of those components are used by this app.
- **The generic radius scale is remapped, not restored and not left at 0.** At 0 those 47 frappe-ui components render square against rounded Glass surfaces; at Tailwind's defaults they render off-ladder. Remapping makes frappe-ui inherit Glass-consistent rounding for free:

  | Step | Value | Glass ladder equivalent |
  |---|---|---|
  | `sm` | 6px | `radius-pill` |
  | `DEFAULT` | 9px | `radius-well` |
  | `md` | 9px | `radius-well` |
  | `lg` | 14px | `radius-input` |
  | `xl` | 17px | `radius-card` |
  | `2xl` | 20px | `radius-panel` |
  | `3xl` | 22px | `radius-tabbar` |

  `none` (0) and `full` (9999px) are unchanged. This lands in **its own commit** with visual verification over `/design` and the four frappe-ui wrappers (`GLinkPicker`, `GDatePicker`, `GToast`, `GAvatar`), never bundled into the Modernist deletion.
- **403 arbitrary Tailwind values** (`text-[8.5px]`, `border-l-[3px]`, `h-[19px]`) hardcode Modernist metrics at call sites and are invisible to a token swap — measured, where earlier drafts said 303. They are swept after the scale exists.

### 16.3 Ionic
- Ionic components are Shadow DOM. Theme via published CSS custom properties and `::part()` only.
- **The `--ion-color-*` ramps are Ionic's internal contract, not app design tokens, and are NOT deleted.** `theme/variables.css` carries 40 hex values across nine ramps (primary/secondary/tertiary/success/warning/danger/dark/medium/light, each with `-rgb`, `-contrast`, `-shade`, `-tint`). Only **`--ion-background-color`, `--ion-text-color` and `--ion-font-family`** map to Glass tokens; the ramps are left alone. Deleting them would break any component using `color="primary"` and gains nothing — they are not part of the palette Glass owns, and no Glass token corresponds to a shade or tint step. They stay hand-written in `variables.css` and are therefore **exempt from the token-discipline gate**, which is why that file keeps a baseline entry rather than being cleaned.
- `ion-content` → `--background: transparent` so the page's light field shows through.
- `ion-tab-bar` host is positionable — the floating pill is achievable without replacing the component. Per-tab navigation stacks are retained.
- `ion-modal` / `ion-action-sheet` → `--background`, `--border-radius`, `--backdrop-opacity`.
- `CustomIonModal.vue` works around a real Ionic focus-trap bug. **Retain it.** Reskin via CSS vars only.
- The global `prefers-reduced-motion` block must also suppress Ionic page transitions; verify it does not break the View Transitions theme reveal.

### 16.4 Specimen route
A `/design` route inside the app rendering all 28 components in every state, in both themes, on device. The spec's HTML specimens are the right idea; they must live in the app so they cannot drift. `frappe-ui`'s `.story.vue` convention is a reasonable model.

### 16.5 CI gates
1. Lint: no hex literals, no arbitrary Tailwind values, no `outline: none` without replacement, no raw `ion-*` styling outside the theme layer
2. Contrast test over the §14.2 matrix, run on every change to `tokens.json`
3. Playwright visual regression per component per theme at 390 × 844
4. axe pass per screen
5. Glass-surface counter per screen against §15

Without gates, §2's "no one-off hex values" is a wish.

### 16.6 Copy
All label changes ship as **Frappe Translation records** — the PWA's `translationsPlugin` reads `frappe.boot.__messages` and supports context. **Zero code change.** Scope by context so the new wording does not leak into Desk.

### 16.7 Two open defects to fix in the same release
1. **Duplicate punch submissions** — implement the 60-second guard in §11.5
2. **Night-shift check-in state** — the check-in / check-out button state must derive from the employee's open shift, not the calendar date. Night-shift staff whose shift spans midnight are currently offered "Check In" in the morning when they need "Check Out"

---

## 17. Copy changes — label only, no logic

| Current | New |
|---|---|
| Attendance Request | Fix a missing punch |
| Compensatory Leave Request | Replacement leave |
| Request Overtime | Claim overtime |
| Request Leave | Apply for leave |
| Submit | Send to approver |
| You have no leaves allocated | No leave allocated yet — P&C are setting this up |

**Rule.** An action keeps the same name through the whole flow. If the button says "Send to approver", the confirmation says "Sent to approver" — not "Submitted successfully".

**Do not change any label not listed here.** Where a system term appears somewhere this document does not cover, flag it rather than renaming it.

---

## 18. Sign-off checklist

Per screen, in both themes, on the lowest-spec device available.

- [ ] Matches the mockup at 1× on 390 × 844 — spacing, radii, weights, tracking
- [ ] Exactly one primary action, and it is opaque
- [ ] All numbers tabular and aligned
- [ ] Every state built: populated, empty, loading, error, offline, disabled, **pending**
- [ ] Theme switch causes no layout shift
- [ ] **Reduce-transparency mode causes no layout shift**
- [ ] 60fps sustained while scrolling; **6 glass surfaces or fewer**
- [ ] **No blob centre inside the content column**
- [ ] **No `mix-blend-mode` layer above any glass surface**
- [ ] Contrast measured against the brightest point of the light field
- [ ] **Two-tone focus ring visible on every control via keyboard**
- [ ] **No opacity multiplier on any ink token**
- [ ] Reduced motion honoured, including Ionic page transitions
- [ ] 120% font scaling without clipping
- [ ] Tab bar clears the safe area — **and `viewport-fit=cover` actually parses**
- [ ] No system vocabulary visible anywhere in the interface
- [ ] Duplicate-submission guard verified by rapid double-tap
- [ ] Night-shift check-out verified with a shift crossing midnight
- [ ] **Check-in screen legible outdoors at midday on the target handset**

---

## 19. Decisions required before build

| # | Decision | Blocks |
|---|---|---|
| 1 | Desktop `lg:` in scope? — **resolved: in scope, §20 governs** | §10 component contracts |
| 2 | Tab bar five — confirm `HOME · ATTEND · LEAVE · PAY · MORE` | §13.1, information architecture |
| 3 | Accept iOS focus-zoom, or raise input font-size to 16px | §13.2 |
| 4 | Name the lowest-spec device in the fleet | §15, §18 |
| 5 | Type floor 10px — P&C sign-off on the change from the mockup | §4.2 |
| 6 | `frappe-ui` upgrade 0.1.105 → 0.1.278 in this programme, or after | §16.1 sequencing |

---

## 20. Desktop layout

DECISION 1 is resolved: desktop is in scope (§13.3). There is no desktop mockup — **this section is the desktop reference**, holding the role the mockup holds for mobile. The §1 conflict rule reads accordingly at `lg:`: where a value here disagrees with the mobile mockup, this section governs above the breakpoint.

### 20.1 Breakpoint

One breakpoint: `lg:` — **1024px**, matching `SideNav.vue`'s existing usage. Below `lg:` the mobile layout in §12 applies unchanged. There is **no tablet layout**; a 900px viewport gets the mobile layout, full stop. A second breakpoint is a second layout to test on every screen in every state — it earns its place only when a real tablet population shows up in analytics.

### 20.2 Navigation

- The tab bar (§10 #8) is hidden at `lg:` — already the case (`lg:hidden`).
- `SideNav` becomes a **glass surface** (§6 recipe), retaining its existing 72px collapsed / 216px expanded widths and its collapse toggle.
- **Top group** — the direct tab destinations from §13.1 in the same order: `HOME · ATTEND · LEAVE · PAY`. More is a container, not a destination; at `lg:` it dissolves.
- Below a divider (1px `--hair`), the contents of More as a **flat list** in §13.1's order: KPI, Issues, SOPs, Expenses, Team, Remote Approvals. **No nested menus.**
- Surface accounting: the SideNav surface **replaces** the tab bar surface in the §15 count — net zero against the budget.

### 20.3 Content column

`max-width: 720px`, **left-aligned against the sidebar**, not viewport-centred. Screen gutter stays 15px (§5).

Rationale: at 1440px a centred full-width column strands 12.5px row labels in whitespace — the eye travels further than the content deserves. 720px is a **starting value**, expected to be tuned once on device; it is a single token (added in phase 4 with the shell, not before), not a structural decision.

### 20.4 Light field

Fixed to the **viewport**, not the content column. Blob centres remain outside the content column per §3.3, which continues to apply at every breakpoint — the column moved, the constraint did not. Blob sizes scale with the viewport; the `blob-opacity` tokens are unchanged.

### 20.5 Grid reflow

| Grid | Mobile | `lg:` |
|---|---|---|
| Balance grid | 2 columns | 4 columns |
| Stat tiles | 3-up | 3-up |

Nothing reflows beyond 4 columns. §15.2 flattening applies at **both** breakpoints: the balance panel stays one glass surface with internal `--hair` dividers — 2×2 becomes 1×4, the surface count does not move.

### 20.6 Unchanged at `lg:`

| Invariant | Ruling |
|---|---|
| Type scale (§4.2) | Identical. Extra width becomes whitespace, **never larger type** |
| Touch targets | 44px minimum retained — input is mixed mouse and touch |
| Glass surface budget (§15) | **6**, unchanged. Desktop shows more at once, which makes §15.2 flattening more important, not less |
| Tokens, radii, spacing, motion | Identical — no desktop-only token exists except the 720px column (phase 4) |

### 20.7 Component implications

Every component contract in §10 must specify `lg:` behaviour **where it differs**. The default is **"identical at both breakpoints"** and is not restated per component. Of the 28, those that differ:

| # | Component | `lg:` behaviour |
|---|---|---|
| 6 | Balance card | Card identical; its parent grid reflows per §20.5 (flattened panel 2×2 → 1×4) |
| 8 | Tab bar | Hidden. SideNav is the navigation surface (§20.2) |
| 24 | App header | **Avatar hidden** — the side nav carries identity at `lg:` (§20.2) — and a **date kicker appears** beside the title. Both are the shipped `BaseLayout.vue` behaviour, preserved rather than invented |
| 25 | Modal / bottom sheet | Presents **centred** at content-column width — a viewport-wide bottom sheet is a mobile idiom. Focus-trap workaround retained (§16.3) |
| 26 | Action sheet | Same ruling as #25: centred dialog, not a full-width bottom strip |

The side nav itself sits in §10.3's treatment list and is specified by §20.2. The remaining 23 components are identical at both breakpoints.

**Hover** — the mockup defines no hover states because it had no pointer. At `lg:` every interactive component reuses its **pressed-state background as hover** (rows: `--icon-bg` at the `row-tap` duration). No new tokens, and hover is never the only signal (§14).

---

*HR Frappe · Glass — Implementation Specification v1.6 · 20 August 2026 · NSTY Holding Sdn Bhd, Group People & Culture. Paired with `HR_FRAPPE_Glass_Light_and_Dark_2.html`. Where the two disagree the mockup governs, except for the eight exceptions recorded in §14.4.*

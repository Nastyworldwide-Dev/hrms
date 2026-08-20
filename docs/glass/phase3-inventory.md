# Phase 3 inventory — retiring Modernist

Analysis only. Nothing in this document has been changed in code; it is the
plan prompts 3.2–3.4 execute. Every count below is measured, not estimated.

Spec: `HR_Frappe_Glass_Spec_v1.1.md` (v1.2). Baseline: `design/lint-baseline.json`.

---

## 1. The 479 lint violations

479 across 65 files. Classified by literal value rather than by occurrence,
because the same value repeats across many files and takes one decision.

| Class | Count | Share |
|---|---|---|
| **REPLACE** — a Glass token already exists | **291** | 61% |
| **ABSORB** — belongs inside a G* component | **80** | 17% |
| **DELETE** — dead with Modernist | **60** | 13% |
| **PROMOTE** — belongs in the Tailwind theme as a named scale entry | **48** | 10% |

### 1.1 By rule

| Rule | Occurrences | Distinct values |
|---|---|---|
| `arbitrary` (Tailwind `[…]`) | 403 | 97 |
| `hex` | 72 | 46 |
| `colorfn` (`rgba()`) | 4 | 4 |

### 1.2 Heaviest files

| File | Total | Breakdown |
|---|---|---|
| `theme/variables.css` | **47** | hex 47 |
| `components/CheckInPanel.vue` | 32 | hex 13 · rgba 3 · arbitrary 16 |
| `views/sop/SopList.vue` | 31 | arbitrary 31 |
| `views/Profile.vue` | 30 | arbitrary 30 |
| `views/sop/SopFormSheet.vue` | 25 | arbitrary 25 |
| `components/SideNav.vue` | 23 | hex 3 · arbitrary 20 |
| `views/RemoteApprovals.vue` | 16 | arbitrary 16 |
| `views/team/TeamDashboard.vue` | 16 | arbitrary 16 |
| `views/issues/HRIssueBoard.vue` | 15 | arbitrary 15 |
| `views/Login.vue` | 13 | arbitrary 13 |
| … 55 more files | 231 | |

**One file is 10% of the total.** `theme/variables.css` holds 47 hex values,
all of them Ionic's default `--ion-color-*` ramps. Phase 3 deletes that file,
so those 47 clear without a single component edit — see §6.

### 1.3 Classification by value group

**REPLACE — 291.** A Glass token already carries this value, or the §4.2
closed-scale ruling (v1.2) resolves it to the nearest step.

| Group | Count | Replacement |
|---|---|---|
| `text-[11px]` `text-[15px]` `text-[13px]` `text-[10px]` `text-[22px]` `text-[9px]` `text-[12.5px]` `text-[11.5px]` `text-[8.5px]` `text-[8px]` `text-[12px]` `text-[30px]` `lg:text-[19px]` … | 172 | §4.2 steps. **Note:** `text-[9px]`, `text-[8.5px]`, `text-[8px]` (17 uses) are below the 10px floor §4.2 raised — these get **larger**, a deliberate legibility change, not a like-for-like swap |
| `tracking-[0.08em]` `tracking-[0.1em]` `tracking-[0.05em]` `tracking-[0.06em]` … | 38 | tracking is part of each §4.2 step; it travels with the size |
| Modernist palette hex in components (`#0B313A`, `#f3f2f2`, `#191817`, `#a1eec9`, `#2E2E2E`, `#242424` …) | 25 | `--g-*` colour tokens |
| Tailwind-default hex (`#dc2626`, `#2563eb`, `#3b82f6`, `#111827`, `#f9fafb` …) | 18 | `--g-danger-ink`, `--g-accent-ink`, `--g-ink*` |
| `leading-[1.05]` `leading-[1.08]` … | 8 | line-height is part of each §4.2 step |
| `pt-[18px]` `px-[18px]` `gap-[18px]` … | 26 | §5 spacing tokens (`pad-action` is 17px 18px) |
| `rgba(…)` overlays | 4 | `--g-scrim`, `--g-lift`, `--g-accent-glow` |

**ABSORB — 80.** The value is correct but belongs inside a component, not at a
call site.

| Group | Count | Absorbs into |
|---|---|---|
| `h-[18px]` `w-[18px]` `w-[17px]` `h-[17px]` `h-[15px]` `w-[15px]` `h-[19px]` `w-[19px]` `h-[22px]` | 51 | §9's icon convention — 14×14 in a 27×27 well. Today every call site picks its own icon size |
| `border-t-[3px]` | 14 | **`GModal`, not `GBanner` — corrected in 3.2.** These are `border-t-[3px] border-inkbase` on bottom-sheet containers: the Modernist sheet *top edge*, not §10.1 #10's 3px left rule. Under Glass the sheet carries a radius and a rim, so this value does not survive the swap at all |
| `w-[34px]` `h-[34px]` | 10 | `GAvatar`'s `size` prop — already absorbed in 2.4 |
| `max-h-[calc(100vh-5rem)]` | 10 | `GModal` sheet ceiling. Reclassified whole: 3.1 split this 5 ABSORB / 5 PROMOTE, but it is one shape with one owner |
| `border-l-[3px]` | 2 | The side-nav active indicator — belongs to the **phase 4 shell** (§20.2), not to any phase 3 component |

**PROMOTE — 48.** No Glass token exists and none should; these are real scale
entries the Tailwind theme should name.

| Group | Count | Promote to |
|---|---|---|
| `underline-offset-[3px]` | 13 | `textUnderlineOffset.DEFAULT` |
| `z-[100]` `z-[1000]` | 16 | a named `zIndex` scale — currently three magic layers with no ordering contract, and `GModal`'s scrim sits at 10000 |
| `max-w-[720px]` `max-w-[620px]` | 9 | **§20.3's content column.** The spec already says 720px "is a single token" — this is where it lands |
| `max-h-[calc(100vh-5rem)]` (remainder) | 5 | `maxHeight.sheet` |
| misc one-offs | 5 | case by case |

**DELETE — 60.** Dies with Modernist; no replacement needed.

| Group | Count | Why |
|---|---|---|
| `theme/variables.css` Ionic `--ion-color-*` ramps | 47 | Replaced wholesale by `glass.variables.css`. **See the §6 caveat — this is not free.** |
| Modernist-only decoration (`.m-poster`, `.m-statnum` call sites) | 8 | Primitives with 1 use each, superseded |
| Dead `--color-*` references | 5 | Modernist vars with no Glass equivalent and no remaining reader |

---

## 2. The 14 `.m-*` primitives

Usage counted across `frontend/src/**/*.{vue,js}`.

| Class | Uses | Files | Superseded by | Note |
|---|---|---|---|---|
| `.m-chip` | 63 | 13 | `GBadge` / `GStatusChip` | Highest-traffic primitive in the app |
| `.m-kicker` | 52 | 30 | eyebrow type step (§4.2) | **Widest spread — 30 files.** Not a component: a type token applied inline |
| `.m-chip-muted` | 18 | 11 | `GStatusChip` (draft/cancelled) | |
| `.m-chip-outline` | 15 | 11 | `GStatusChip` (cancelled) | |
| `.m-chip-solid` | 13 | 11 | `GBadge` (open) / `GStatusChip` (rejected) | |
| `.m-avatar-sq` | 8 | 7 | **`GAvatar` — DELETED, not ported** | Exists only to force frappe-ui's Avatar to radius 0. Under Glass the rounding returns |
| `.m-btn-primary` | 7 | 6 | `GButton` | |
| `.m-rule` | 6 | 3 | `--g-hair` divider | |
| `.m-bar` | 5 | 3 | `GBalanceCard` / `GKraPanel` | Track must become `--track-solid` (§6.3) |
| `.m-bar-band` | 2 | 2 | **`GBalanceCard` — already absorbed** | Ported in prompt 2.2, behaviour intact |
| `.m-row` | 2 | 1 | `GListRow` | |
| `.m-bar-fill` | 1 | 1 | `GBalanceCard` / `GKraPanel` | |
| `.m-poster` | 1 | 1 | — | Single use; delete outright |
| `.m-statnum` | 1 | 1 | `GStatTile` | |

**Total: 194 usages across the 14 classes.**

Two are not component swaps and should not be planned as such:
- **`.m-kicker` (52 uses, 30 files)** is a *type* treatment, not a component.
  It swaps to the eyebrow step, which is a mechanical find-and-replace and by
  far the widest-touching change in the phase.
- **`.m-avatar-sq` (8 uses)** is deleted, not swapped. Removing it is what
  *restores* rounding to frappe-ui's Avatar — the class is a Modernist
  suppression, and deleting it is the change.

---

## 3. Files depending on `modernist.css` / `variables.css`

**Direct imports — 2, both in `src/main.js`:**
```
src/main.js:30  import "./theme/variables.css"
src/main.js:33  import "./theme/modernist.css"
```

**Indirect dependants — 12 files** consuming `--m-*`, `--font-heading`,
`--font-body` or `--color-*`:

`ListView.vue` · `AttendanceCalendar.vue` · `ExpenseAdvancesTable.vue` ·
`ExpenseTaxesTable.vue` · `FilePreviewModal.vue` · `ExpensesTable.vue` ·
`WorkflowActionSheet.vue` · `FormView.vue` · `BottomTabs.vue` ·
`sop/SopFormSheet.vue` · `sop/SopDetail.vue` · `kpi/Dashboard.vue`

**Plus `tailwind.config.js`**, whose `extend.colors` resolves entirely through
`--m-*` triplets (`ink.100–900`, `accent.*`, `ground`, `surface`, `inkbase`,
`divider`). Those Tailwind utilities are used app-wide, so **deleting
`modernist.css` breaks every `text-ink-*` / `bg-ground` / `border-divider`
utility in the app**, not just the 12 files above. This is the dependency that
sets the sequence in §7.

**One hidden coupling:** `CheckInPanel.vue:986` documents that its modal
centring comes from a *global* rule in `modernist.css`. Deleting the file
changes that component's layout. There may be more global rules with no
comment — the file needs reading in full before deletion, not grepping.

---

## 4. The Archivo CDN link

Four dependency points, all reachable:

| Where | What it does |
|---|---|
| `index.html:183–193` | The CDN `<link>` + 2 preconnects |
| `tailwind.config.js:35` | `fontFamily.sans: ["Archivo", …]` — **the app's default face** |
| `theme/modernist.css:46,48` | `--font-heading`, `--font-body` |
| `theme/variables.css:11` | `--ion-font-family` |

**What breaks when the link goes:** every one of those four falls back to
`system-ui`. Because `fontFamily.sans` is the Tailwind default, that is *every
element in the app* that does not explicitly set a family — not only the 12
files in §3. Glass's own components are unaffected: they set
`--g-font-display` / `--g-font-ui` explicitly and those resolve to self-hosted
Inter/Inter Tight (prompt 1.4).

**Therefore the link must be removed in the same change that repoints
`fontFamily.sans`, never before it.** Removing it alone is a visible
app-wide regression; removing it after the repoint is a no-op.

---

## 5. The zeroed `borderRadius` scale — highest risk, and not where expected

`tailwind.config.js` zeroes `sm / DEFAULT / md / lg / xl / 2xl / 3xl`.
`none` (0) and `full` (9999px) are unaffected by a restore.

### 5.1 App source — near zero

Exhaustive grep of `frontend/src/**/*.{vue,js}` for any `rounded*` token:

| Utility | Uses | Files |
|---|---|---|
| `rounded` (bare) | 3 | `FormField.vue`, `ForgotPassword.vue`, `ChangePassword.vue` |
| `rounded-t-lg` | 2 | `FilePreviewModal.vue` |
| `rounded-b-sm` | 1 | `FormField.vue` |
| ~~`rounded.to`~~ | — | **False positive** — a JS variable in `utils/formatters.js:37`, not a class |

**Six real usages across four files.** The claim in §16.2 that "~103 files
rely on `rounded-*` being 0" **does not hold for app source.** It is off by
roughly two orders of magnitude.

### 5.2 frappe-ui — where the blast radius actually is

`tailwind.config.js` includes frappe-ui in its content glob:
```
"./node_modules/frappe-ui/src/components/**/*.{vue,js,ts,jsx,tsx}"
```
So frappe-ui's own components are compiled against the zeroed scale:

| Utility | Uses in frappe-ui |
|---|---|
| `rounded` (bare) | 66 |
| `rounded-lg` | 20 |
| `rounded-md` | 14 |
| `rounded-xl` | 4 |
| `rounded-sm` | 2 |
| **Total** | **106 across 47 component files** |

**17 of those components are used by this app:** Autocomplete, Avatar, Badge,
Button, Calendar, DatePicker, DateTimePicker, Dialog, Dropdown, ErrorMessage,
FeatherIcon, FormControl, Input, Popover, Select, Switch, Toasts.

### 5.3 What visibly changes on restore

Restoring the scale rounds **every frappe-ui surface at once**: dialog corners,
autocomplete popovers, dropdowns, toasts, buttons, inputs, avatars, switches.
In app source it changes exactly six spots.

**This is the goal, not the hazard.** Glass wants the rounding back — the
zeroed scale exists solely for the Modernist flat look. The hazard is that it
lands in one commit across 17 third-party components with no per-component
review, and that four Glass components (`GLinkPicker`, `GDatePicker`,
`GToast`, `GAvatar`) currently wrap or skin frappe-ui and were built and
reviewed *against the zeroed scale*.

**Recommendation:** restore the scale in its own commit that touches nothing
else, so the diff is one config change and the review is a visual pass over
the specimen and the four wrappers. Do not bundle it with the Modernist
deletion.

---

## 6. Two findings that change the plan

**6.1 `variables.css` cannot simply be deleted.** It holds 47 hex values, and
the 40 of them forming Ionic's `--ion-color-*` ramps (primary/secondary/
tertiary/success/warning/danger/dark/medium/light, each with rgb/contrast/
shade/tint) have **no Glass equivalent**. `glass.variables.css` deliberately
generates only the five variables that map (prompt 1.2), and §16.3 says Ionic
is themed through published custom properties only. Deleting the ramps leaves
every Ionic component that resolves `--ion-color-*` — buttons, toggles,
action-sheet defaults, `ion-refresher` — falling back to Ionic's built-in
palette, which is not the Modernist palette *or* the Glass one.

Options, needing a ruling before 3.4:
1. Keep the `--ion-color-*` block, migrate its values to Glass tokens, and
   accept 40 hex values moving into the generated file (they would then be
   generated, not hand-written, so the lint gate stays clean).
2. Delete the ramps and audit which Ionic components actually resolve them.
3. Keep `variables.css` as a thin Ionic-palette-only file after the Glass
   variables move out.

**Option 1 is the recommendation** — it is the only one that keeps a single
source of truth, which is the entire point of the phase.

**6.2 The §16.2 "303 arbitrary values / 103 files" figure is wrong in both
directions.** Measured: **403 arbitrary values**, and the `rounded-*` claim
that motivated calling the radius scale high-risk applies to 4 app files, not
103. The radius restore is genuinely lower-risk than the spec implies; the
*type* sweep (`.m-kicker` across 30 files, 172 `text-[…]` replacements) is
higher-risk than the spec implies, because 17 of those sizes get **larger**
under the §4.2 floor.

---

## 7. Proposed sequence

The assumption in the prompt — promote/absorb first, then swap `.m-*` to `G*`,
then delete Modernist and restore the radius last — is **correct in order but
wrong in packaging**: it puts two independent high-risk changes (the Modernist
deletion and the radius restore) in the same step. The inventory says split
them.

### 3.2 — Promote and absorb
Add the promoted scale entries to `tailwind.config.js` (zIndex, content
column 720px per §20.3, underline-offset, sheet max-height) and absorb the 80
ABSORB values into the G* components that own them. **Touches no view.**

*Why first:* every later step replaces call sites with these names. Without
them, 3.3 has nowhere to point. Nothing here changes rendering — the values
are identical, only their home changes — so it ships with zero visual risk.

### 3.3 — Replace call sites, `.m-*` → `G*`
The 291 REPLACE values and the 194 `.m-*` usages, in one sweep per file.
`.m-avatar-sq` is deleted here (8 uses), not swapped.

*Why second:* it depends on 3.2's names existing, and must precede the
deletion — `modernist.css` cannot go while 194 usages still reference it.
**This is the largest and riskiest step** (30 files for `.m-kicker` alone, 17
type sizes changing), and the one to split further if any step needs splitting.

*Sub-order within 3.3:* type first (`.m-kicker` + `text-[…]`, mechanical and
verifiable by the lint gate), then chips (`.m-chip*`, 109 uses → `GBadge` /
`GStatusChip`), then the low-count primitives.

### 3.4 — Delete Modernist
Repoint `tailwind.config.js`'s `extend.colors` off `--m-*` onto `--g-*`,
delete `modernist.css`, resolve `variables.css` per the §6.1 ruling, repoint
`fontFamily.sans`, and remove the Archivo link **in the same commit** (§4).

*Why last:* §3's finding — the Tailwind colour utilities resolve through
`--m-*`, so deleting `modernist.css` before the repoint breaks `text-ink-*`
and `bg-ground` app-wide. Read `modernist.css` in full first for undocumented
global rules like the one `CheckInPanel.vue:986` depends on.

### 3.5 — Restore the borderRadius scale *(new, split out of 3.4)*
Its own commit, touching only `tailwind.config.js`. Review is a visual pass
over `/design` and the four frappe-ui wrappers.

*Why separate:* §5.3 — it changes 17 third-party components at once and is
the one change in the phase whose review is visual rather than mechanical.
Bundled into 3.4 it would be invisible inside a large deletion diff.

---

## 8. The usage gate

`design/gates/usage.mjs`, wired into `yarn gates` as gate 5.

Current reading: **0 violations, empty baseline** — no view or non-glass
component touches a Glass class yet, which is the correct starting state.
Verified against a probe file carrying all three violation types: all three
fire and the gate exits 1.

Rules: `glass-class` (using `.g-glass` directly), `hand-panel` (a Glass radius
plus a background on one line), `direct-import` (importing
`glass-components.css`). Exempt: `components/glass/**` and the specimen.

It becomes `--strict` at the start of phase 5.

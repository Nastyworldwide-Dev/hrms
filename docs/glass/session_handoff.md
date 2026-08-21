# Session handoff — Glass phase 8

State at the end of the 8.6+ pass. Read this before picking the work back up.

**Branch** `nz-glass` at `559079695`, pushed and in sync · **Spec** v1.10 ·
working tree clean apart from the vestigial `frappe-ui` submodule.

**All six gates green. 143 findings -> 54. P0 20 -> 0. 23 root causes -> 3.**

```
lint     OK  194 known, 0 new        a11y    OK  76 screen-themes, 34 baselined, 0 new
usage    OK  0 known, 0 new          visual  OK  0 differing
contrast OK  54 pairs, 0 failed      surfaces OK 41 screens, 0 over 6
```

---

## 1. What landed in 8.6+

**a11y fixed at source, not baselined.** The 50 screen-themes carrying
serious/critical debt were never 62 separate bugs. `button-name` on 46 of them
was **four icon-only controls** repeated across the app — a frappe-ui `<Button
variant="ghost">` around a bare icon. `GIconButton` takes a **required** `label`
prop, so the name cannot be forgotten; the component will not render without it.
That one component also closed the 28×28 target and the chevron-vs-arrow back
drift. `aria-required-children` was one calendar claiming `role="grid"` with no
rows or gridcells.

**A class name has one owner — and one place that owns it.** v1.8 recorded the
first half (`.g-field` defined twice inside the theme file). This pass found the
second: a component's `<style scoped>` compiles to `.class[data-v-xxxxxxx]`,
which outranks a plain class **including inside a media query**. Seven classes
were shadowed; **two changed behaviour**:

- `GSegmented` — `min-height: 38px`, justified by arithmetic that does not hold
  ("38px visual + 3px track padding = the 44px target"; the track's padding is
  not part of the option's box). Every segmented option was under §14.1 and the
  theme layer's correct value never applied.
- `GAppHeader` — `display: flex` on `.g-header__avatar-link`, defeating the
  theme's `lg:` rule that hides it because §20.2 gives identity to the side nav.
  Desktop rendered the avatar in the header **and** the name in the side nav.

All seven moved into the theme layer. `lint` gained a `scopedOverride` rule,
verified by reintroducing a collision (0 → 1, gate fails; restored, passes).

**§14.1 targets are hit-tested, not measured.** `getBoundingClientRect` cannot
see a `::before`-expanded hit area, and the app uses those deliberately — the
token says "padded out to 44px WITHOUT moving the visual". Measuring produced
false positives; a gate with those gets ignored. `undersizedTargets()` in
`frontend/e2e/screens.mjs` asks the browser what is at the point, ignores the
floating tab bar (it covers content at rest by design) and ignores off-viewport
points. It is folded into the a11y gate as a `target-size` rule. Ten screens
report **zero**. It found one real defect measuring never would: the two month
steppers sat 8px apart while each expands 6px per side, so their targets
overlapped and one stole the other's half.

**The three 7.3 rulings ran.** Two-column `lg:` grids removed from Home, Leave
and Attendance; Attendance's stack order is 1..7 with the action list where the
anatomy puts it; §12 records that form screens are server-ordered, `GNotePanel`
is deleted, and §21 "drawn but not built" names every zero-consumer component.

**Both of your rulings are recorded**, so they stop resurfacing: the tab bar
belongs to the tab root (§12), and the a11y baseline shrinks rather than being
accepted (§16.5.1).

Plus: one empty-state component instead of three; the dashed rim means "nothing
here" only; three empty states that promised an action have one; a catch-all
route; and the vendor wordmark is translatable — proven end to end, the header
renders "NSTY People" from one Translation record.

---

## 2. What ran, and what it found

All three outstanding items completed.

**Re-shoot** — 266 captures / 342 files against the 8.6+ build, no failures, no
slow screens.

**a11y re-baseline** — **50 screen-themes / 106 nodes -> 22 / 41**, then 34
after one more source fix. Not accepted: `label` on 16 screen-themes turned out
to be **one component** (`FormField`'s Time input labels via a sibling `<span>`,
not a `<label for>`), the third time this pass a large count collapsed to a
shared component. Remaining: `aria-allowed-attr` 8, `label` 8 (a
differently-shaped detail-screen variant), `target-size` 4, and three rules at 2.

**Six-gate pass** — five green first time; `visual` failed with 2, and that
failure was the gate working. Both were `notifications`, whose **relative
timestamps** ("in 4 hours" -> "in 5 hours") make its baseline fail an hour after
it is shot. Self-changing elements now carry `data-visual-mask` and the gate
excludes them. Verified by re-running against committed baselines 15 minutes
old, so the timestamp had genuinely drifted: 0 differing.

### Three gate-reporting defects, all of which read as green

Worth carrying forward, because none was a fault in what the gate *checked*:

1. `a11y` printed three serious violations and called `process.exit(0)`.
2. `visual` reported `FAIL ?` with no reason — `run.mjs` capped every gate at
   six minutes and SIGTERMed it with its output still buffered.
3. `visual` compared against baselines **it had written itself**: Playwright
   rewrites `__` to `-` when it resolves a snapshot path, so the `__` names the
   capture wrote could never be found. It created a parallel set and passed
   against its own output. Only a file-count mismatch — 368 where 342 were
   expected — surfaced it.

Each is fixed, and each was verified by forcing the failure it is meant to
catch rather than by reading the code.

---

## 3. Standing caution — the remaining findings are inference-flagged

`docs/glass/frontend-audit.md` lists 143 findings, of which **54 remain**
(0 P0, 32 P1, 22 P2). **Treat every cause in it as unverified.** Across 8.1–8.5, **five findings were wrong, and all five
failed the same way**: an accurate observation with a wrong cause inferred on
top of it.

- "Detail screens do not scroll" — my capture script scrolled `ion-content`
  while `FormView` owns an inner `overflow-y-auto`. The pages scroll fine.
- "The design specimen is blank" — `/design` is `import.meta.env.DEV` only and
  compiled out of production.
- "Issue rows show no subject", "the DETAILS section is empty", "no light field
  on 7 list screens" — my own seed data and content density, not the app.

A screenshot is evidence of *what rendered*. It is never, on its own, evidence
of *why*. Verify the cause before acting on any remaining finding — and prefer
measuring the DOM over reading the image, which is how all five were caught.

Two more from this pass: RC13's dashed empty state is **spec-correct**
(§10.1 #11) — the dropzone was the collision, and it moved. And the a11y "62
bugs" were six shared components.

**Still open (3 of 23 root causes):** RC18 the avatar has three forms · RC19 the
double-letter gap, cause unknown, needs a device · RC22 the tab bar on list
screens, which is **intended** and recorded in §12, not a defect.

---

## 4. Environment

- Site `verify-bench/fresh.local`, served on **:8080** (`bench serve`), employee
  `HR-EMP-00001` — *Nurul Aisyah binti Abdul Rahman*, seeded by
  `docs/glass/audit/seed.py`. `AUDIT_PW` is required by every render-time tool.
- Seeding artifacts that are **not** defects: leave rows showing `0d`, balance
  bars at 100%, `_Test Company`, empty KPI and Team screens.
- `/hr/issues` silently redirects to the staff view without an HR role — the two
  captures are byte-identical, so the HR board has never actually been audited.

# Session handoff — Glass phase 8

State at the end of the rulings pass. Read this before picking the work back up.

**Branch** `nz-glass` at `5269bf1cd`, pushed and in sync · **Spec** v1.12 ·
working tree clean apart from the vestigial `frappe-ui` submodule.

**All eight gates green, nothing skipped.**

```
lint     OK  194 known, 0 new       tokens     OK  3 bindings, 5 collapses, 0 new
usage    OK  0 known, 0 new         a11y       OK  76 screen-themes, 28 baselined, 0 new
contrast OK  54 pairs, 0 failed     visual     OK  0 differing
surfaces OK  41 screens, 0 over 6   coherence  OK  38 screens, 0 violations
```

`visual` reads 0 because all 64 diffs were classified first — see
`visual-classification.md`. 61 were the rulings landing, 0 were regressions, and
3 were date rot that is now masked rather than baked into a baseline. The last
time this gate read green it was comparing against its own output; it isn't now,
because the same gate failed with 64 real diffs one run earlier.

`a11y` went from 34 baselined entries to 28: the rulings cleared 8 and
introduced none.

## 1. What landed in the rulings pass

Seven rulings, each verified by **measuring the DOM** rather than reading a
screenshot — the discipline that caught five wrong causes in 8.1–8.5.

| # | Ruling | Measured |
|---|--------|----------|
| 1 | No primary on a navigation hub | Four actions are peer `GListRow`s in one panel. Screens with >1 filled action **1 → 0** |
| 2 | Light field owned by the shell | Peak fields during a push **3 → 1**; `backdrop-filter` intact at `blur(20px) saturate(1.8)` |
| 3 | `bg-accent` is the brand fill | Across 38 light screens: accent-ink fills **8 → 0**, brand fills **15 → 26**, all `GButton` |
| 4 | One section-header treatment | Six treatments → one `.g-eyebrow` |
| 5 | `GPage` owns back navigation | With back **26 → 31**, without **12 → 7** — exactly the tab-root set |
| 6 | A create action is a `GButton` | White header pills retired |
| 7 | replacement-leave on the shared shell | Duplicate *New Claim* removed |

**Ruling 2 overturned a spec clause.** §3.2 required the light field inside the
page to survive Ionic's backdrop-root, and that fear does not hold: every
ancestor carries `contain: size layout style`, which creates **no** backdrop
root — only `paint` does, along with `filter`, `opacity < 1` and mask. The only
root a push creates is a page at `opacity: 0`. §3.2 now records the measurement,
not the assumption.

**Ruling 3's real finding was not the one ruled on.** `accent.DEFAULT` resolved
to `--accent-ink` while `accent-100` resolved to `--brand`, so `bg-accent`
painted dark olive and the name meant the opposite of what it said. The 50
existing uses were renamed to explicit `-accent-ink` **first**, so flipping
`DEFAULT` changed nothing that was already correct.

---

## 2. The three new gates — and what they catch that nothing could before

The app acquired six header treatments, a back control on 26 screens and not on
12 with no rule connecting them, and one role rendered as a chartreuse
`GButton` on dashboards and a white frappe-ui pill on lists — **all of it
passing six green gates**. That is not six gates failing. It is six gates
answering a question that was never the one being asked.

**Gate 7 — `tokens` (static, no site).** `lint` could already say `bg-accent`
was not a raw hex. It could not say the name meant the opposite of what it
said, because the name is spelled correctly. Two checks:

- *Role–token binding* — asserts the alias a **role** depends on resolves to the
  token that role requires. Three bindings pinned.
- *Token collapse* — pairs distinct in one theme and identical in the other.
  This is the mechanism, and `brand|accent-ink` turned out to be one of **five**:

```
brand|accent-ink   danger|danger-ink   success|success-ink
warn|warn-ink      glass-fill|hair                    (all dark-only)
```

Four of those nobody was looking for. Each is a place a fill/ink swap renders
*correctly* in the only theme this app was ever screenshotted in. That is how
the olive submit button survived a 148-finding audit.

**Gate 8 — `coherence` (rendered, 38 screens).** Every other gate asks "is this
screen right?" once per screen; none compares screen A to screen B. It profiles
every screen and asserts four cross-screen invariants: one primary and it is the
primary component, back navigation follows one rule, one empty-state component,
one section-header treatment. It runs in **light** theme deliberately —
`--accent-ink` equals `--brand` in dark, so a brand/ink swap renders correctly
there and every dark screenshot ever taken of this app was blind to it.

First run: one violation, `remote-approvals` carrying an ad-hoc empty state
instead of `GEmptyState`. Now composed.

**And that fix produced the third catch.** Removing the ad-hoc empty state took
the only focusable child out of the scroll region, so `a11y` fired
`scrollable-region-focusable` on `ot-requests` in both themes — a keyboard user
could not scroll it at all. Fixed at the shared `ListView` container, not on
`ot-requests`, because **every list hits this the moment it is empty**;
`ot-requests` was only the one empty in the seed.

Three gates chaining a fix into the defect it caused, inside one pass, is the
argument for running them per root cause rather than at session end.

---

## 3. What landed in 8.6+

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

## 4. What ran, and what it found

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

## 5. Standing caution — the remaining findings are inference-flagged

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

## 6. Environment

- Site `verify-bench/fresh.local`, served on **:8080** (`bench serve`), employee
  `HR-EMP-00001` — *Nurul Aisyah binti Abdul Rahman*, seeded by
  `docs/glass/audit/seed.py`. `AUDIT_PW` is required by every render-time tool.
- **The credential lives in `.env` at the repo root — gitignored, mode 600.**
  Load it with `set -a; . .env; set +a`. The value is not in the repo and must
  not be put there.
- **If it is missing or a gate SKIPs at a 401, run
  `docs/glass/audit/reset-audit-pw.sh`.** It mints a new password, resets the
  audit user, and rewrites `.env`. `seed.py` only ever *consumed* `$AUDIT_PW`
  (`u.new_password = SECRET`) and never stored it, so the value dies with the
  shell that set it — which stalled three sessions before the script existed.
  The script deliberately does **not** re-run `seed.py`: re-seeding changes
  content, content changes screenshots, and that would corrupt every
  visual-regression comparison against the committed baselines.
- Seeding artifacts that are **not** defects: leave rows showing `0d`, balance
  bars at 100%, `_Test Company`, empty KPI and Team screens.
- `/hr/issues` silently redirects to the staff view without an HR role — the two
  captures are byte-identical, so the HR board has never actually been audited.

---

## 7. Pick up here

Nothing is blocked. The credential problem that stalled three sessions is
fixed at the root: `.env` holds it, `docs/glass/audit/reset-audit-pw.sh`
regenerates it. Run the suite with:

```bash
set -a; . .env; set +a; node design/gates/run.mjs
```

Open, in rough order of value:

1. **`coherence` reports 225 of 284 uppercase runs not using `.g-eyebrow`, and
   does not enforce it.** The note says chips and tab labels are uppercase too,
   which is true and is why it is unenforced — but 225 is not a number anyone
   has actually looked through. Ruling 4 consolidated the six *section-header*
   treatments; it did not establish which of these 225 are section headers. Until
   someone classifies them the way the 64 visual diffs were classified, this
   gate is reporting a number rather than asserting a rule.
2. **The 0.2% visual tolerance hides small type-colour shifts at 1440.** Ruling
   4's eyebrow recolour is real on `home-1440-dark` and sat under the threshold.
   Not a bug — but it means `visual` is not the instrument for small colour
   changes, and nobody should read a green `visual` as proof a colour is right.
3. **Three root causes remain from the 8.6+ audit** (§5): RC18 the avatar has
   three forms · RC19 the double-letter gap, needs a device · RC22 the tab bar
   on list screens, which is intended and recorded in §12.

A full-suite run cleans `test-results/`, so read any diff images before
starting another gate.

---

## 8. The spec was arguing with itself

Found while re-examining §3.2, and worth more than the ruling that surfaced it.

§0's v1.11 change log recorded the light field as **shell-owned, one
instance**. §3.2's *body* still read "the light field must be rendered inside
each page's stacking context — never as a global background on `ion-app` or
`body`." Opposite rules, same document, one version apart. The implementation
followed the change log; anyone reading §3.2 top-down would have "fixed" the
app back into the defect.

The old rule rested on one unmeasured assumption: that Ionic's `transform`/
`opacity` transitions make every page a permanent backdrop root. What is
actually true — measured, not read:

- Backdrop roots come from `filter`, `opacity < 1`, a mask, and `contain:
  paint`. The ancestors here carry **`contain: size layout style`**, which
  creates none.
- The only backdrop root a push creates is the outgoing page at `opacity: 0`,
  which is not visible.
- Peak simultaneous fields during a push **3 → 1**; `backdrop-filter` intact at
  `blur(20px) saturate(1.8)`.

So the per-page rule prevented a blur failure that cannot happen, and caused a
real one instead — three opaque fields painting at once during a push, which a
human saw. Shell ownership is correct and is what ships (`App.vue:15`;
`GLightField.vue` has no suppression logic and needs none — with one field
there is nothing to suppress). §3.2 is rewritten to the measurement and now
names what *would* break it, so the next person re-measures instead of
re-assuming. Spec **v1.12**.

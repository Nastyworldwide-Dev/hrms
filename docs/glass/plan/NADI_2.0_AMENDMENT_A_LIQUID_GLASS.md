# Amendment A — Liquid Glass stays; reachability and accessibility become gates

Status: proposal for Nabil's approval, 10 September 2026. Branch `nz-glass`.
Amends [NADI_2.0_UX_PLAN.md](NADI_2.0_UX_PLAN.md) (8 Sep) and
[NADI_2.0_SURFACE_MAP.md](NADI_2.0_SURFACE_MAP.md) (9 Sep), neither approved.
No application code changed by this document.

Nabil, 10 Sep: "Keeping and further applying the Liquid Glass design properly
and accordingly. The goal here is to improve current Nadi PWA UX flow,
usability, accessibility, reachability and readability without compromising
the functionality and aesthetic wise (liquid glass)."

The plan as written cannot deliver that sentence, because its first decision
retires Liquid Glass. This amendment reverses that decision, keeps everything
the plan got right, and adds the three goals the plan never encoded as rules.

---

## A0. What is actually wrong today (measured, not asserted)

The plan's evidence against Glass is real. It indicts the *placement*, not the
material. Three facts from the shipped code:

| Fact | Where | Consequence |
|---|---|---|
| `.g-glass` — the **content card** surface class, referenced in **26 files** (21 of them consuming surfaces; the other 5 are the three theme files, `data/theme.js` and the specimen page) — carries `backdrop-filter: blur(20px) saturate(180%)`, and so does `.g-glass-ghost` | `frontend/src/theme/glass-components.css:320-325`; `--g-blur-panel: 20px` at `glass.css:84` | Every content card is frosted. Text is read *through* a moving tint. |
| A three-blob colour field sits behind the whole app: lime `rgba(200,255,0,.72)` 230px, teal `rgba(0,229,192,.62)` 210px, purple `rgba(123,92,255,.66)` 180px, all at `blur 36px` | `design/tokens.json` → `field.*`; `GLightField.vue:32-34` | What the cards are frosting is decoration, not content. Card contrast shifts with scroll position. |
| The token set already had to invent `track-solid` — "an opaque track behind disputable numbers… a number a person may dispute with their manager must not be read through a moving tint. On the track, muted text fell to **3.41:1** (dark) / **4.14:1** (light), both below WCAG AA" | `design/tokens.json` description | The codebase has **already conceded** that glass-on-content fails AA, and patched around it once. |

That third row is the finding. The team did not need a new decision; it needed
to apply the one it already made, everywhere, instead of once.

**Liquid Glass is a material for chrome that floats over moving content.** Blur,
refraction and a lit rim exist to say "this layer is *above* the page". Applied
to the page itself it says nothing and costs legibility.

There are exactly **four** `backdrop-filter` sites in `frontend/src`, and they
split two and two:

| Selector | Kind | Verdict |
|---|---|---|
| `ion-tab-bar.g-tabbar` (`glass-components.css:172-190`) | chrome | **already correct** — fill, 1px `glass-rim`, blur 20 + `saturate(180%)`, both inner rim shadows, an opaque `@supports` fallback and a `prefers-reduced-transparency` fallback. This is the reference implementation of U16. |
| `.g-sidenav` (`glass-components.css:262-267`) | chrome (§20.2 desktop) | correct; §15.3 records that at `lg:` it replaces the tab bar's surface for net zero against the glass budget. |
| `.g-glass` (`:320-325`) | **content** | retire the blur (Q0a). |
| `.g-glass-ghost` (`:344`) | **content** | retire the blur (Q0a). |

So the shipped app is not "flat chrome over frosted content". It is **one chrome
surface done exactly right, three chrome surfaces never given the material at
all** (header, sheets and their scrim, toast — none carries `backdrop-filter`),
**and the material spent on content instead.** U16 is therefore not new work
imposed on the codebase: it is the tab bar's own treatment, applied where it was
missed and withdrawn where it does not belong.

---

## A1. Q0 is reversed and split in two

The plan's Q0 reads: *"The prototype's flat, still material becomes the spec…
the Glass light field, bevel and blur retire."* It bundles two independent
decisions. They are now separate.

| # | Replaces | Decision | Recommendation |
|---|---|---|---|
| **Q0a** | Q0, first half | Retire the three-blob light field (`GLightField`, `field.*` tokens) and the blur on `.g-glass` content cards. Content sits on an opaque, still surface. | **Yes.** This is what the prototype's flatness was actually asking for, and `track-solid` already proved the case. |
| **Q0b** | Q0, second half | Retire Liquid Glass as the material. | **No — reversed.** Glass is kept and *concentrated* on the chrome layer, per rule U16 below. |

Consequence for the plan's own text: every "flat white", "retire blur", "retune
to flat" verdict in surface map §1.3 applies to **content surfaces only**. The
chrome rows in that table (tab bar, side nav, header, sheets, toast, floating CTA) are
re-scoped by U16 and keep their material.

Consequence for phase 9 decisions D2/D3: they are amended, not retired. The
surface map (§0, `NADI_2.0_SURFACE_MAP.md:37`) claimed the reversal "retires two
months of Glass work on purpose". It does not. It relocates it — and as A0 shows,
the tab bar's share of that work becomes the spec rather than being thrown away.

---

## A2. Three new contract rules (§2 of the plan gains U16–U18)

Same format as U1–U15. **G** = machine gate, **R** = review with a fixture.

| # | Rule | Why (evidence) | Gate |
|---|---|---|---|
| **U16** | **Glass is chrome-only.** `backdrop-filter` is permitted on exactly **seven** surfaces: tab bar (`ion-tab-bar.g-tabbar`), desktop side nav (`.g-sidenav`, §20.2 — it replaces the tab bar's surface at `lg:` for §15.3 net zero), app header, sheets and their scrim, toast, the floating primary CTA, and the check-in card's action layer. Every other surface is opaque. Each glass surface carries the full material — blur, `saturate`, a 1px lit rim (`glass-rim`), and both inner rim shadows — never blur alone, and always with the opaque `@supports` and `prefers-reduced-transparency` fallbacks the tab bar already ships. | `.g-glass` and `.g-glass-ghost` blur content today; `track-solid` already conceded glass-on-content fails AA (A0). The first two surfaces are built and correct — the rule codifies them; the other five are the work. | **G**: a CSS gate over `frontend/src/theme/*.css` and `.vue` blocks — `backdrop-filter` outside the seven-selector allowlist fails the build. Extends `design/gates/surfaces.mjs` (which counts `.g-glass` today, `surfaces.mjs:39`). |
| **U17** | **Reachability.** On a 390×844 device the primary action of every tab-root screen sits in the bottom third (y ≥ 563). Destructive actions sit outside it. Sheets place their primary action at the bottom, above the safe area. Nothing interactive lives in the top-right corner except the header's single right action. Minimum target 44×44 with 8px separation. | The plan has no reachability rule at all. U13 governs scroll, nothing governs thumbs. Home's check-in CTA — the most-used control in the app — sits at y≈200 today. | **G**: `frontend/e2e/app-measure.mjs` gains a `primaryActionY` and `targetSize` assertion per route, run against the seeded site. |
| **U18** | **Readability floor.** Body and label text ≥ 12px; list-row titles ≥ 15px; every text/background pair ≥ 4.5:1 (3:1 for ≥ 18px bold) **measured against the opaque composite**, in both themes. No text is ever composited over a blurred or animated backdrop. | Tokens today: `caption` 10.5px, `row-label` 12.5px, `badge` 10px uppercase — all below the floor (surface map §1.4). Contrast measured on glass fell to 3.41:1. | **G**: `design/gates/contrast.mjs` already **enforces** contrast (`contrast.mjs:251` exits 1 on any failure; 54 pairs, 0 failures on HEAD) — the gap is that no branch protection makes it blocking (A3). The **type-size** assertion is new work: no gate reads a font size today (`grep -rln 'font-size' design/gates/` returns nothing), so 0.6a builds it. |

---

## A3. Accessibility moves from Phase 4 to Phase 0

The plan puts all accessibility in "Phase 4 — Polish (Track B)", last, behind a
served site. With accessibility named as a goal, that ordering is wrong: every
slice in phases 1–3 would be built, reviewed and shipped before a single
accessibility check ran, and the fixes would then be a retrofit across ~55
commits.

**Correction, 10 Sep (review of 8c902d849).** An earlier draft of this section
called these gates "advisory". They are not. Both exit non-zero on failure and
`glass-gates.yml` runs `yarn gates` on push to `nz-glass` and on pull request.
The escape hatches are different, and knowing which one is open changes what
slice 0.8 has to do:

| Gate | File | What is actually true today | Amended |
|---|---|---|---|
| axe pass, both themes | `design/gates/a11y.mjs` | **Enforcing when it runs** (`a11y.mjs:111` exits 1 on any new serious/critical above baseline). But it is a render-time gate: with no served site and no `AUDIT_PW` it prints `{"status":"skip"}` and **exits 0** — which is the CI condition today, so a11y has never actually been measured in CI. Baseline carries **30 nodes** across 16 `route:theme` entries / 8 distinct routes: `label` ×16, `aria-allowed-attr` ×8, `button-name` ×2, `aria-dialog-name` ×2, `target-size` ×2. | `glass-gates.yml` serves a site with `AUDIT_PW` and runs `yarn gates --strict`, where a skip is fatal (`verdict.mjs`). Baseline frozen and may only go down — which needs `--update-baseline` (`a11y.mjs:32`) removed or CI-guarded, or "frozen" is unenforceable. |
| contrast | `design/gates/contrast.mjs` | **Enforcing.** Static, so it runs every invocation; `contrast.mjs:251` exits 1 on any failure. Green on HEAD: 54 pairs, 0 failures. | No gate change needed. Add the U18 **type-size** assertion (new — nothing reads a font size today). |
| surfaces | `design/gates/surfaces.mjs` | Enforcing; counts `.g-glass` (`surfaces.mjs:39`). | Extended to enforce the U16 seven-selector allowlist. |
| **branch protection** | repo setting | **Absent.** `gh api …/branches/nz-glass/protection` → 404. A red `Glass gates` job blocks no merge. | This — not the gate files — is what "required check" means. Nabil enables it. |

So the real gap is two things the plan never named: **CI has no served site, so
the a11y gate silently skips**, and **nothing is blocking, because the branch is
unprotected**. Fixing either gate file would have changed nothing.

New slice **0.8**, sized with the rest of phase 0:

> **0.8 — Make accessibility actually run, then clear the baseline.**
> (a) `glass-gates.yml` serves a site with `AUDIT_PW` and runs `yarn gates --strict`,
> so a render-time skip is fatal. (b) Remove or CI-guard `--update-baseline`.
> (c) Fix the **30 baselined nodes**: 22 are labels, button names, a dialog name
> and two touch targets — mechanical; the other **8 are `aria-allowed-attr`**,
> which is ARIA misuse and may need markup changes, so size them separately.
> (d) Nabil enables branch protection on `nz-glass` with `Glass gates` required.
> Done when: `a11y-baseline.json` is `{}`, the gate runs (not skips) in CI, and a
> deliberate breach turns the job red **and blocks the merge**.

Phase 4 keeps what genuinely needs a served site and a finished UI: 320px
reflow, reduced motion, visual baseline refresh, and the both-themes sweep.

---

## A4. Decoupling the readability fixes from the material decision

Surface map §1.4 raises `caption` 10.5→12, `row-label` 12.5→15, and drops
uppercase tracking on pills and eyebrows. Those are **correct and independent of
Q0**. As the plan is written they arrive inside slice 0.6 ("token re-tune"),
which is framed as the go-flat slice — so rejecting Q0 would have lost them.

Slice 0.6 is therefore split:

- **0.6a — Readability and grid re-tune.** The four-point grid (§1.1), the
  six-step spacing scale (§1.2) and the twelve type roles (§1.4). Independent
  of Q0a/Q0b. Ships first.
- **0.6b — Material re-tune.** Retire `field.*` and `GLightField`; move
  `backdrop-filter` off `.g-glass` and onto the U16 chrome allowlist; give each
  chrome surface its rim and inner shadow. Blocked on Q0a + Q0b.

---

## A5. What this changes in the plan, line by line

| Plan location | Change |
|---|---|
| §2 contract | Gains U16, U17, U18. |
| §5 Q0 | Replaced by Q0a (yes) and Q0b (no — glass stays). Q1–Q10 unchanged. |
| §6 phase 0 | 0.6 splits into 0.6a / 0.6b. New 0.8 (make a11y run in CI, then clear the 30-node baseline). Phase 0 goes 7 slices → 9. |
| §6 phase 0.3 mockup | The mockup is no longer "the prototype IS the visual contract". It is **the prototype's structure, spacing and type on Liquid Glass chrome** — flat opaque content, glass chrome. Sign-off is on that composite, per screen family. |
| §6 phase 4 | Keeps 320px reflow, reduced motion, visual baselines, both themes. Loses the a11y sweep to 0.8. |
| §8 risks | New row: *retiring the light field changes every visual baseline at once* → guard: 0.6b is its own commit, baselines refreshed deliberately, `design/gates/visual.mjs` diff reviewed screen by screen. |
| Surface map §0 | Q0 recommendation replaced by A1. |
| Surface map §1.3 | "flat white / retire blur" verdicts scoped to content surfaces; the chrome rows re-scoped by U16. Its "Card → retune: flat white, radius 16" verdict stands; its tab-bar row keeps the material it already has. |

Everything else in both documents stands: the gap ledger (§3), the eight
corrections to the mapping doc (§4), Q1–Q10, phases 1–3, and every measured
number in the surface map. This amendment touches the material decision and the
gate ordering only.

---

## A6. What I need from you

| # | Question | Recommendation | Blocks |
|---|---|---|---|
| 1 | Q0a — retire the three-blob light field and the blur on content cards? | Yes | 0.6b |
| 2 | Q0b — keep Liquid Glass, concentrated on the seven chrome surfaces (U16), using the tab bar's existing treatment as the reference? | Yes (this is the reversal you asked for) | 0.6b, 0.3 mockup |
| 3 | U17 reachability rule — primary action in the bottom third on tab roots? | Yes | 2.1, 2.2 |
| 4 | Slice 0.8 now, not Phase 4: give CI a served site so the a11y gate stops skipping, and clear the 30-node baseline? | Yes | phase 1 start |
| 5 | Does 0.3 produce a mockup of the amended look before any phase 1 code? | Yes — glass chrome over flat content, six screen families | phase 1 start |
| 6 | Will you enable branch protection on `nz-glass` with `Glass gates` as a required check? Only you can; without it every gate in this plan is advisory **by policy**, whatever the exit codes say. | Yes | 0.8 done-condition |

Nothing is built until these six have your word. Q1–Q10 in the original plan
remain open and unchanged; they are not re-asked here.

---

## A7. Review record

Reviewed by `frappe-reviewer` on commit `8c902d849` (docs-only; `ruff` had no
Python target, `bench run-tests --app hrms` exit 0, `yarn test` 271 pass / 4
pre-existing `pushNotifications.test.js` harness failures untouched by a
markdown diff). It ran the design gates rather than reading them and returned
two Critical and three Warning findings, all `class: spec`. Every one is
corrected above: the a11y counts (8/20 → **30 nodes**), "advisory" (both gates
are **enforcing**; the open holes are the CI skip and the missing branch
protection), `--update-baseline` as an unenforceable "frozen", `.g-sidenav`
missing from the U16 allowlist, and three attribution/precision fixes.

One finding of the reviewer's own was itself wrong, and correcting it improved
the argument: it confirmed "the tab bar carries no `backdrop-filter`", repeating
the error in the draft it was checking. `ion-tab-bar.g-tabbar`
(`glass-components.css:172-190`) carries the complete material, fallbacks
included. That is why A0 now names it the reference implementation of U16
instead of an example of flat chrome.

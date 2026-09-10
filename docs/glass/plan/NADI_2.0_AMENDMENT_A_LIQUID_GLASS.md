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
| `.g-glass` — the **card** surface class, used in **26 files** — carries `backdrop-filter: blur(20px) saturate(180%)` | `frontend/src/theme/glass-components.css:320-325` | Every content card is frosted. Text is read *through* a moving tint. |
| A three-blob colour field sits behind the whole app: lime `rgba(200,255,0,.72)` 230px, teal `rgba(0,229,192,.62)` 210px, purple `rgba(123,92,255,.66)` 180px, all at `blur 36px` | `design/tokens.json` → `field.*`; `GLightField.vue:32-34` | What the cards are frosting is decoration, not content. Card contrast shifts with scroll position. |
| The token set already had to invent `track-solid` — "an opaque track behind disputable numbers… a number a person may dispute with their manager must not be read through a moving tint. On the track, muted text fell to **3.41:1** (dark) / **4.14:1** (light), both below WCAG AA" | `design/tokens.json` description | The codebase has **already conceded** that glass-on-content fails AA, and patched around it once. |

That third row is the finding. The team did not need a new decision; it needed
to apply the one it already made, everywhere, instead of once.

**Liquid Glass is a material for chrome that floats over moving content.** Blur,
refraction and a lit rim exist to say "this layer is *above* the page". Applied
to the page itself it says nothing and costs legibility. The shipped app has it
exactly backwards: the chrome is nearly flat, the content is frosted.

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
chrome rows in that table (tab bar, header, sheets, toast, floating CTA) are
re-scoped by U16 and keep their material.

Consequence for phase 9 decisions D2/D3: they are amended, not retired. The
plan claimed the reversal "retires two months of Glass work on purpose". It
does not. It relocates it.

---

## A2. Three new contract rules (§2 of the plan gains U16–U18)

Same format as U1–U15. **G** = machine gate, **R** = review with a fixture.

| # | Rule | Why (evidence) | Gate |
|---|---|---|---|
| **U16** | **Glass is chrome-only.** `backdrop-filter` is permitted on exactly six surfaces: tab bar, app header, sheets and their scrim, toast, the floating primary CTA, and the check-in card's action layer. Every other surface is opaque. Each glass surface carries the full material — blur, `saturate`, a 1px lit rim (`glass-rim`), and an inner shadow — never blur alone. The `@supports not (backdrop-filter)` fallback stays opaque and legible. | `.g-glass` blurs 26 content files today; `track-solid` already conceded glass-on-content fails AA (A0). Blur without a rim is a smudge, not a material — the six chrome surfaces are where refraction carries meaning. | **G**: a CSS gate over `frontend/src/theme/*.css` and `.vue` blocks — `backdrop-filter` outside the six-selector allowlist fails the build. Extends `design/gates/surfaces.mjs`. |
| **U17** | **Reachability.** On a 390×844 device the primary action of every tab-root screen sits in the bottom third (y ≥ 563). Destructive actions sit outside it. Sheets place their primary action at the bottom, above the safe area. Nothing interactive lives in the top-right corner except the header's single right action. Minimum target 44×44 with 8px separation. | The plan has no reachability rule at all. U13 governs scroll, nothing governs thumbs. Home's check-in CTA — the most-used control in the app — sits at y≈200 today. | **G**: `frontend/e2e/app-measure.mjs` gains a `primaryActionY` and `targetSize` assertion per route, run against the seeded site. |
| **U18** | **Readability floor.** Body and label text ≥ 12px; list-row titles ≥ 15px; every text/background pair ≥ 4.5:1 (3:1 for ≥ 18px bold) **measured against the opaque composite**, in both themes. No text is ever composited over a blurred or animated backdrop. | Tokens today: `caption` 10.5px, `row-label` 12.5px, `badge` 10px uppercase — all below the floor (surface map §1.4). Contrast measured on glass fell to 3.41:1. | **G**: `design/gates/contrast.mjs` promoted from advisory to a **required check**; the type-role gate asserts the floor values. |

---

## A3. Accessibility moves from Phase 4 to Phase 0

The plan puts all accessibility in "Phase 4 — Polish (Track B)", last, behind a
served site. With accessibility named as a goal, that ordering is wrong: every
slice in phases 1–3 would be built, reviewed and shipped before a single
accessibility check ran, and the fixes would then be a retrofit across ~55
commits.

The gates already exist and are simply not required checks:

| Gate | File | Today | Amended |
|---|---|---|---|
| axe pass, both themes | `design/gates/a11y.mjs` | advisory, **8 accepted violations** in `design/a11y-baseline.json` (`label` ×9, `aria-allowed-attr` ×5, `button-name` ×2, `target-size` ×2, `aria-dialog-name` ×2) | required check. The baseline is **frozen at today's count and may only go down**; a slice that adds a violation cannot commit. |
| contrast | `design/gates/contrast.mjs` | advisory | required (U18) |
| surfaces | `design/gates/surfaces.mjs` | counts `.g-glass` | extended to enforce the U16 allowlist |

New slice **0.8**, sized with the rest of phase 0:

> **0.8 — Clear the accepted a11y baseline.** Fix the 20 outstanding violations
> (they are labels, button names and two touch targets — no redesign needed),
> empty `a11y-baseline.json`, and promote a11y + contrast to required checks.
> Done when: the baseline file is `{}` and a deliberate breach turns the gate red.

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
| §6 phase 0 | 0.6 splits into 0.6a / 0.6b. New 0.8 (a11y baseline to zero). Phase 0 goes 7 slices → 9. |
| §6 phase 0.3 mockup | The mockup is no longer "the prototype IS the visual contract". It is **the prototype's structure, spacing and type on Liquid Glass chrome** — flat opaque content, glass chrome. Sign-off is on that composite, per screen family. |
| §6 phase 4 | Keeps 320px reflow, reduced motion, visual baselines, both themes. Loses the a11y sweep to 0.8. |
| §8 risks | New row: *retiring the light field changes every visual baseline at once* → guard: 0.6b is its own commit, baselines refreshed deliberately, `design/gates/visual.mjs` diff reviewed screen by screen. |
| Surface map §0 | Q0 recommendation replaced by A1. |
| Surface map §1.3 | "flat white / retire blur" verdicts scoped to content surfaces; the six chrome rows re-scoped by U16. |

Everything else in both documents stands: the gap ledger (§3), the eight
corrections to the mapping doc (§4), Q1–Q10, phases 1–3, and every measured
number in the surface map. This amendment touches the material decision and the
gate ordering only.

---

## A6. What I need from you

| # | Question | Recommendation | Blocks |
|---|---|---|---|
| 1 | Q0a — retire the three-blob light field and the blur on content cards? | Yes | 0.6b |
| 2 | Q0b — keep Liquid Glass, concentrated on the six chrome surfaces (U16)? | Yes (this is the reversal you asked for) | 0.6b, 0.3 mockup |
| 3 | U17 reachability rule — primary action in the bottom third on tab roots? | Yes | 2.1, 2.2 |
| 4 | Accessibility promoted to a required check now (slice 0.8), not Phase 4? | Yes | phase 1 start |
| 5 | Does 0.3 produce a mockup of the amended look before any phase 1 code? | Yes — glass chrome over flat content, six screen families | phase 1 start |

Nothing is built until these five have your word. Q1–Q10 in the original plan
remain open and unchanged; they are not re-asked here.

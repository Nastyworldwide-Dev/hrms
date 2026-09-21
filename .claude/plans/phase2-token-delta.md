# Phase 2, section 3: the token delta between the shipped system and Mockup 4

Section 3 of the brief is "a cohesive, production-quality Liquid Glass
interface — not scattered transparency and blur effects". The shipped app
already HAS that system. So section 3 is not authoring a design system; it is
reconciling two that overlap by 53 tokens. This file is that reconciliation,
measured. It changes nothing.

Method: the first (light `:root`) and dark-block declarations of every `--g-*`
property in `frontend/src/theme/glass.css` (generated from `design/tokens.json`)
compared against the same in `Nadi PWA UI UX 2.0/nadi-2.0-mockup-4.html`.
Counts: 196 shipped, 62 in the mockup, 53 names shared.

Do not diff against `glass.variables.css` — that is output 3 of
`build-tokens.mjs` and holds only 5 Ionic `--ion-*` variables. `glass.css` is
output 1 and is the `--g-*` file. I diffed the wrong one first and got a
nonsensical "zero overlap".

## Values that differ on a shared name — 5 of 53

Four in light, one in dark. Everything else is byte-identical, which is the
real headline: **the mockup is already 92% the shipped system.**

### 1. `--g-glass-fill` — the only one that is a design decision

|        | shipped                   | mockup                |
|--------|---------------------------|-----------------------|
| light  | `rgba(255,255,255,.56)`   | `rgba(255,255,255,.86)` |
| dark   | `rgba(255,255,255,.075)`  | `rgba(42,46,56,.86)`   |

This is the same defect, solved two different ways.

`family-mockup4.md` CLASS A (61 instances) blamed exactly the shipped light
value: at .56 the fill is a VEIL, so the decorative blobs composite through it
and secondary ink lands on a backdrop nobody chose — measured 4.10:1 in light
and 2.00:1 in dark. The mockup's fix was to raise the fill to .86 and, in dark,
change it from white-on-dark to an opaque-ish slate. That is why the mockup also
needs `--g-glass-solid` and `--g-well-solid`, which the shipped system has no
equivalent for.

**The shipped app fixed the same class a different way and it holds.**
`design/gates/contrast.mjs` composites glass over the app background and then
asserts ink over each blob at its strongest alpha INSIDE the content column.
It passes: 54 checks, 0 failures, `ink-muted over blob` 4.54–4.56 in both
themes. The mechanism is §3.3 blob PLACEMENT — no blob centre reaches the
content column — rather than a thicker veil.

So adopting .86 is not a bug fix on the app. It is a change of visual language:
more opaque glass, less of the field showing through. `tokens.json` says of this
exact token — *"Light is deliberately more opaque than dark; do not correct
(spec 6)"*. **Owner's call, and it is the single biggest visual difference
between the two.** Note the dark value especially: .075 white vs an opaque
slate is the difference between "tinted air" and "a card".

### 2. `--g-content-column-lg` — 720px shipped, 880px mockup

`tokens.json` calls 720px *"a starting value, expected to be tuned once on
device — which is why the spec insists it be a single token"*. The mockup tuned
it. This is the token doing its job; 880px is adoptable with no argument.
Caveat: the contrast gate's blob-clearance proof is computed against the
content column, so widening it moves the column toward the blobs. Re-run
`node design/gates/contrast.mjs` after the change — it is a one-line check, not
a risk, but it is not free either.

### 3 & 4. `--g-font-display` and `--g-font-ui` — order, not content

Same faces, different first entry. Shipped leads with `-apple-system`; the
mockup leads with `'Inter Tight'` / `Inter`.

|          | shipped first | mockup first |
|----------|---------------|--------------|
| display  | `-apple-system` | `'Inter Tight'` |
| ui       | `-apple-system` | `Inter` |

**Do not adopt the mockup's order without deciding this deliberately.** The
mockup pulls both faces from Google Fonts over the network (`<link>` at line
10). The app does not: `frontend/src/theme/fonts.css` self-hosts Inter Tight
from `@fontsource-variable`, latin subset only, and explicitly does NOT load a
second copy of Inter because frappe-ui already ships it. Leading with the
system font is what makes first paint instant on iOS; leading with Inter makes
every screen wait on a font that, for Inter proper, is loaded by another
package. This is a performance decision wearing a typography costume.

## Names in the mockup with no shipped token — 9

| token | mockup value (light / dark) | what to do |
|---|---|---|
| `--g-elev-1/2/3` | `none` / two-layer / `0 10px 30px` | **Naming collision, not a gap.** Shipped has `--g-lift` (`0 10px 30px rgba(20,26,40,.10)`) and `--g-shadow-action`. Same idea, different scheme: the mockup numbers elevation, the app names it by role. Pick ONE. Numbered elevation is the more conventional 2026 practice; role-named is what 196 shipped tokens and every component already use. Renaming is a 196-token sweep for no user-visible gain — recommend keeping the shipped scheme and mapping `elev-2 -> lift`. |
| `--g-glass-solid`, `--g-well-solid` | `#F4F6F8` / `#15171D`, `#E8EAEE` / `#101219` | Only needed because of the .86 fill above. Decide `--g-glass-fill` first; these follow from it. `--g-radius-well: 9px` exists shipped with no matching surface colour, so a `well` role is half-present already. |
| `--g-sat` | `180%` | **Adopt.** The app hard-codes `saturate(180%)` at six sites in `glass-components.css`. That is exactly the literal the lint gate exists to catch, and the mockup already names it. Cheap, real, low risk. |
| `--g-badge-bg` | `#C81E1E` | A red count badge. The app's unread indicator (`.g-header__dot`, glass-components.css:1967) is an 8px dot painted `var(--g-brand)` — chartreuse, no count. Different component, not a missing token. Only needed if the owner wants counted badges. |
| `--g-train`, `--g-travel` | `#F472B6`, `#38BDF8` | Calendar day markers (`.m-tr`, `.m-tv`). The app has `--g-leave` and uses `--g-brand` for OT, but no training/travel marker — the only shipped mention of travel is `cancelRule.js:19`, a business rule, not a colour. **These are new product surface, not a restyle**: adding them means the calendar renders event types it does not render today. Belongs with the IA question, not with tokens. |

## What this means for sequencing

Three of the five value diffs are adoptable now and touch `tokens.json` only:
`--g-sat` (new), `--g-content-column-lg` (720 -> 880). That is a small,
gate-checkable commit with no screen work.

The other two are decisions, not edits:

1. **`--g-glass-fill` .56 -> .86** — changes the entire feel of every panel in
   both themes, and contradicts a "do not correct" note already in
   `tokens.json`. The app's contrast is currently PASSING by a different
   mechanism, so this buys taste, not correctness.
2. **font stack order** — buys the mockup's look at the cost of first paint,
   and would mean loading Inter twice unless the shipped self-hosting is kept.

Both are the same shape as the tab question in
`phase2-ground-truth.md`: visual contract vs. something bigger. Neither should
be picked by me.

Nothing here was changed. `design/gates/contrast.mjs` was run read-only to
confirm the shipped system's current state: 54 checks, 0 failures.

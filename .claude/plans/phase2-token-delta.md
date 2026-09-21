# Phase 2, section 3: the token delta between the shipped system and Mockup 4

Section 3 of the brief is "a cohesive, production-quality Liquid Glass
interface — not scattered transparency and blur effects". The shipped app
already HAS that system. So section 3 is not authoring a design system; it is
reconciling two that already overlap almost completely. This file is that
reconciliation, measured. It changes nothing.

Method: the first (light `:root`) and dark-block declarations of every `--g-*`
property in `frontend/src/theme/glass.css` (generated from `design/tokens.json`)
compared against the same in `Nadi PWA UI UX 2.0/nadi-2.0-mockup-4.html`.
Counts: 196 shipped, 62 in the mockup. Light and dark are SEPARATE passes over
different name sets, and the two must not be added together: the light `:root`
blocks share 53 names, the dark blocks share 19.

Do not diff against `glass.variables.css` — that is output 3 of
`build-tokens.mjs` and holds only 5 Ionic `--ion-*` variables. `glass.css` is
output 1 and is the `--g-*` file. I diffed the wrong one first and got a
nonsensical "zero overlap".

**Every number in this file is reproduced by `node
design/tools/mockup-token-diff.mjs`.** Run it rather than trusting the figures
below; re-run it rather than editing them by hand. It exists because four
counts here drifted before it did, each time by quoting a number from one
measurement beside a number from another.

## Values that differ on a shared name

**Light: 49 of 53 shared names identical, 4 differ.**
**Dark: 18 of 19 identical, 1 differs.**

Five differing (token, theme) pairs across four distinct tokens, because
`--g-glass-fill` differs in BOTH passes. Counting the pairs and then dividing
by the light denominator alone is how "5 of 53" gets written — it silently
adds a dark result to a light total. Quote the two lines above, not a merged
ratio.

The headline survives the correction: **almost everything the mockup names,
the shipped system already defines identically.**

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
it. **It is not adoptable as it stands: 880px FAILS the contrast gate.**

Measured, not reasoned about — I copied the gate, changed the one number, ran
it, and deleted the copy:

    [contrast] FAIL lg 1024px nav:216 dark  ink-muted over blob B = 4.31 (min 4.5)
    GATE_RESULT {"gate":"contrast","checked":57,"failures":1,"skipped":0}

At the narrowest desktop width with the side nav expanded, a 880px column
reaches far enough right to sit on blob B, and muted ink over that composite
falls to 4.31:1 — under the 4.5 floor. At 720px the same combination clears
the blob entirely.

**Measuring this turned up a second defect, and it was the more serious one.**
The gate hardcoded `column: 720`; it did not read `--g-content-column-lg` from
`tokens.json`. Editing the token to 880 would have changed the app and left the
gate still proving 720 — green, and wrong. The failure above only appeared
because I changed the gate's own constant by hand.

FIXED, in 59e20f697 and 1aacc7529. The gate now reads the token, so the run
above reproduces by editing `tokens.json` alone. Reviewing that first fix
refuted its own commit message: `column` was not the only copied value —
`gutter: 15`, `const GUTTER = 15` and `VIEWPORT = {w:390,h:844}` were the same
class, and the gutter one was live (60px moves the gate from 54 checks to 42).

Adopting 880 therefore now means two things, not three: widen the token, then
resolve the dark blob-B overlap the new width creates (move blob B, lower its
alpha at `lg`, or cap the column at the narrow end). Still a real piece of
work, not a token edit — but the gate will now tell you so by itself.

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
| `--g-sat` | `180%` | **Adopt.** The app repeats `saturate(180%)` at six sites in `glass-components.css`, and the mockup already names it. Note the lint gate would NOT catch this: `design/gates/lint.mjs` scans for hex/`rgb()`/`hsl()` literals and arbitrary Tailwind values — colour, not filter functions. So this is a duplication no gate is watching, which is a reason to name it, not a violation to clear. Cheap, low risk. |
| `--g-badge-bg` | `#C81E1E` | A red count badge. The app's unread indicator (`.g-header__dot`, glass-components.css:1967) is an 8px dot painted `var(--g-brand)` — chartreuse, no count. Different component, not a missing token. Only needed if the owner wants counted badges. |
| `--g-train`, `--g-travel` | `#F472B6`, `#38BDF8` | Calendar day markers (`.m-tr`, `.m-tv`). The app has `--g-leave` and uses `--g-brand` for OT, but no training/travel marker — the only shipped mention of travel is `cancelRule.js:19`, a business rule, not a colour. **These are new product surface, not a restyle**: adding them means the calendar renders event types it does not render today. Belongs with the IA question, not with tokens. |

## What this means for sequencing

**NONE of the four tokens whose values differ is a free adoption.** I wrote the
opposite first: `--g-content-column-lg` looked like the token doing its job
until I ran the gate at 880 and it failed. The only genuinely cheap change on
this page is `--g-sat`, which is a NEW name rather than a value diff and
therefore does not come out of the four at all.

The four break down as three decisions, not edits — `--g-font-display` and
`--g-font-ui` are one choice made twice:

1. **`--g-glass-fill` .56 -> .86** — changes the entire feel of every panel in
   both themes, and contradicts a "do not correct" note already in
   `tokens.json`. The app's contrast is currently PASSING by a different
   mechanism, so this buys taste, not correctness.
2. **font stack order** — buys the mockup's look at the cost of first paint,
   and would mean loading Inter twice unless the shipped self-hosting is kept.
3. **`--g-content-column-lg` 720 -> 880** — fails the contrast gate at
   1024px/dark. The gate used to hardcode the old width and would not have
   noticed; that is fixed, so the failure is now reproducible from the token.
   See above; this is the one I had wrong.

Both are the same shape as the tab question in
`phase2-ground-truth.md`: visual contract vs. something bigger. Neither should
be picked by me.

Nothing here was changed. `design/gates/contrast.mjs` was run read-only to
confirm the shipped system's current state: 54 checks, 0 failures.

FAMILY LEDGER — Nadi 2.0 mockup 4, measured audit 21 Sep 2026

Three symptoms were reported. Each turned out to be one instance of a class.
Every line below is a measurement, not a reading of the code.

Probes (frontend/_audit/): a2 real-pixel contrast, a3 clipping + depth +
sheet stability, a4/a5/a6 calendar and sheet motion, a7 responsive + targets.
a2 gates itself on a known-flat lime button and refuses to report if that
self-test drifts; it found and survived four of its own false-positive modes
(off-viewport clamping, glyph-stroke sampling, ancestor hit-tests, toast
occlusion) before any number here was trusted.

--------------------------------------------------------------------
CLASS A — text over glass is not guaranteed a substrate.        61 instances
--------------------------------------------------------------------
Reported as: "the drawer ... has contrast issue".
Root cause: --g-glass-fill is rgba(255,255,255,.56) in light and
rgba(255,255,255,.075) in dark. The fill is a VEIL, not a surface, so whatever
sits behind the sheet composites through it. The decorative .field blobs are
behind every sheet, so secondary ink lands on a backdrop the design never
chose. Arithmetic: --g-ink2 #545C68 on the nominal #F4F6F8 is 6.24:1 and fine;
on the backdrop actually measured under the sheet, rgb(199,202,204), it is
4.10:1 and fails. In dark the veil is 7.5% white, i.e. almost none, and ink2
over the lime blob measures 2.00:1.
Why axe said "0 violations": axe cannot evaluate contrast through a
backdrop-filter. It returned 8-71 INCOMPLETE nodes per state and no verdict.
The previous clean bill of health was blind exactly where the defect lives.
Worst instances: dark sheet:rej .field-l 2.00:1 · light day-empty .pill 3.68:1
· dark cal seg "Month" 4.42:1 · 9x .sub, 5x .field-l, 4x .muted, 3x H2.

--------------------------------------------------------------------
CLASS B — an ellipsis that never renders.                        7 instances
--------------------------------------------------------------------
Reported as: "overflow text".
Root cause: text-overflow:ellipsis has no effect on display:inline. .trunc is
applied to inline <span>s, which lay out at full natural width, overflow the
parent, and are hard-cut by the first ancestor that clips — with no "..." to
tell the reader a word is missing. The photographed instance, "Not approved —
the kitchen was already short that n", is a 298px span inside a 165px parent,
cut 18px past the .panel edge.
Instances: s:req x3, sheet:new x3, s:anns x1.

--------------------------------------------------------------------
CLASS C — a screen that ends mid-card.                           4 instances
--------------------------------------------------------------------
Reported as: "crowded home that cause scrolling and unclear information".
Measured: home is 1264px of content in a 774px viewport = 1.63 viewports, and
nothing marks the fold, so a card is bisected by it. s:appr is 1.33 viewports
and its first fold cuts the card "Fix a day - 11 Sep" in half.
Instances: s:home 1.63 · sheet:ann 1.63 · appr:staffview 1.63 · clock:out 1.63
· s:appr 1.33 (fold cut) · s:leaveform 1.16 · s:score 1.03 · cal:claim 1.02.

--------------------------------------------------------------------
CLASS D — a sheet whose top edge is wherever its content ends.   4 instances
--------------------------------------------------------------------
Reported as: "calendar has glitchy on click dates. jumpy."
NOT the grid and NOT a missing animation, both of which were measured and
cleared: the grid is byte-identical before and after every tap, and the sheet
does animate (432px -> 0 across 340ms, sampled on rAF). The jump is BETWEEN
days: the sheet is anchored bottom:0 with content-driven height, so tapping
2, 8, 16, 24 in turn puts its top edge at 418, 488, 444, 600 — a 182px swing
under the reader's thumb with no scroll and no resize.

--------------------------------------------------------------------
CLASS E — controls under the 44px floor.                         3 instances
--------------------------------------------------------------------
Measured in CSS pixels, not rect pixels: the mockup renders inside #fit's
transform:scale, so a compliant 44px control reads as 32px through a rect.
.skip 134x40 · .cta "Make your first request" 209x39 · .ghost "Try again" 110x41.

--------------------------------------------------------------------
NOT DEFECTS — measured, then dismissed. Recorded so they are not re-opened.
--------------------------------------------------------------------
axe target-size x13 on desktop — an artifact of the preview scale; nothing is
  under 24px CSS at real size.
.body has no focus ring — it is the skip-link's programmatic target
  (tabindex="-1"); a ring there would fire on every skip. Deliberate, commented.
.field decorative blobs overflow the app frame — they sit inside an
  overflow:hidden parent and are clipped, never painted outside.
Text behind an open scrim or a toast reads low — dimmed on purpose. The probe
  excludes it by paint depth, not by overlap, so a sheet's own rows still count.
Layout at 320/360/390/414/768/1024/1280/1440 — clean, no horizontal overflow,
  tab bar inside the frame at every width.

## CLASS G — one column, two widths (found by screenshot, not by probe)

CAUSE: a `<button>` shrink-wraps its content where a `<div>` fills its parent.
The same `.panel` class measured 338px as a div and 259px as a button, so two
rows under one heading came out ragged.

Why nothing caught it: every probe measured each element against a threshold.
None compared siblings to each other. A 259px panel is a perfectly valid panel;
it is only wrong next to a 338px one.

FIX: `button.panel,button.card,button.ann,button.tile{width:100%;display:block;
text-align:left}` — a surface fills its column whatever element it is built from.
GATE: `_audit/a8.mjs` asserts that surfaces stacked in one column share one left
edge and one width, in every state. Now `COLUMN EDGE CLEAN`.

## CLASS H — text that comes to rest under chrome

CAUSE: the tab bar floats, so there is live page under and around it. Content
scrolled into that strip and STOPPED there: at max scroll the last row sat 6px
inside the gradient with nowhere further to scroll. 12 instances across both
themes.

FIX (two parts, because a fade alone is not enough):
- `.app::after` — content dissolves into the page before it reaches the bar. A
  fade is honest for text on its way past.
- `.body` padding-bottom `+22px -> +42px` — the floor clears the fade's 34px
  reach plus 8px. A fade is dishonest for text that comes to rest in it.
GATE: `_audit/a9.mjs`. At maximum scroll, no text box may overlap the fade or
the tab bar. Now `NO TEXT RESTS UNDER CHROME`.

## Probe defects found while closing G and H

These were false readings, not mockup defects. Each is fixed in the probe and
each would have hidden a real defect later.

1. `offsetParent` lies for a collapsed `<details>`: it stays truthy and the
   element reports a real height, so a2/a3/a9 were all measuring text no one can
   see. `checkVisibility({contentVisibilityAuto,opacityProperty,visibilityProperty})`
   is the only API that answers the question. Fixed in all three.
2. a2 could not see `.app::after`. A pseudo-element is unreachable from
   querySelectorAll, so the overlay list never contained the fade and the probe
   called an intentional cue a contrast defect. Registered by hand from the same
   geometry the stylesheet uses.
3. a2 sampled on exact rects. The toast's rect says y=716; the compositor, with
   a 0.7px transform offset and a 999px radius, had already painted 60% of it
   into row 715. 2px of slack on overlay edges.
4. a2 stepped scroll by 700 from the top and never finished at the bottom, so a
   short screen was only ever measured at scrollTop 0 — the one position where
   its last row is still below the fold. It now always ends at maxScroll.
5. a5 read `getBoundingClientRect().top` on a sheet that slides by TRANSFORM. A
   transformed box reports the same top every frame, so a working 340ms glide
   read as "SNAPS (no entry animation)". It also armed its sampler and called
   openDay in the same task, so the "from" state never painted. Sampling the
   computed transform with a frame in between: 19 distinct positions, 482 -> 0,
   `ANIMATES`.

## Fold-cut ruling (a3 class C)

Six states report a card crossing the first fold. This is NOT a defect where the
card has more cards under it — that is the standard cue that a list continues,
and removing it would make a scrollable screen look complete. It IS a defect
when the cut card is the last one, because then the screen ends mid-card.
a3 now classifies the two cases instead of flagging both; all six current
instances read `(affordance: more below)`, none `LAST CARD`.

## CLASS G2 — ragged INNER edge (same cause, one level down)

CAUSE: a leading `.pill` shrink-wraps its label, so a list of dates ("Thu 18"
44px, "Mon 22" 56px) gave every title a different left edge. Measured: 12px
spread across three rows. It reads as three misaligned rows, not one column.

This is CLASS G's sibling. G was the outer edge of stacked surfaces; G2 is the
text start of stacked rows inside one surface. Both were found by looking at a
screenshot, because both are invisible to any check that measures one element
against a threshold — a 44px pill is a perfectly good pill until it sits above
a 56px one.

FIX: `.row>.pill:first-child{flex:none;min-width:60px;text-align:center}` — a
pill used as a LEADING marker in a stack is a gutter, not a badge, so it gets
one width for all of them.
GATE: `_audit/a8.mjs` second block. Now `INNER EDGE CLEAN`.

Probe defect 6, found by this gate on its first run: a role-gated row
(`class="row rowbtn hide"`, approver-only) still answers querySelectorAll and
reports left=0, which read as a 95px misalignment against its visible siblings.
Same `checkVisibility()` fix as defect 1 — the third place this class of probe
bug appeared, which is why it is now written down rather than fixed in silence.

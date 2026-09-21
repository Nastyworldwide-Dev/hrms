# Mockup-4 audit probes

Measurement scripts for `Nadi PWA UI UX 2.0/nadi-2.0-mockup-4.html`. They are
committed because `docs/glass/HANDOFF.md` names them in its `verify:` line — a
verify command that points at files only one machine has is not a verify
command.

They need Playwright, which resolves from `frontend/node_modules`. Run them
from `frontend/`, not from `/tmp` and not from the repo root.

**The mockup itself is gitignored (`.gitignore:40`).** A fresh checkout has
these probes but not their target, and `lib.mjs` exits 2 with that explanation
rather than a module-not-found error. Un-ignoring the mockup folder is the
owner's call and has not been given.

| probe | asserts |
|---|---|
| a1 | axe-core sweep. Records INCOMPLETE counts; see notes — axe cannot compute contrast through `backdrop-filter`, so its silence is not a pass. |
| a2 | CLASS A. Real-pixel contrast: samples painted pixels, hit-tests every point, self-tests against a known 14:1 face and aborts if that drifts. |
| a3 | CLASS B/C/D. Clipped text, screen depth in viewports, sheet-detent stability. |
| a4 | screenshot capture. |
| a5 | motion. Samples the computed transform, not `getBoundingClientRect().top` — a transformed box reports the same top on every frame. |
| a6 | theme toggle. |
| a7 | responsive sweep 320–1440, tap targets in CSS px, focus visibility. |
| a8 | CLASS G/G2. Ragged outer and inner column edges — sibling-to-sibling, since neither shows up against a threshold. |
| a9 | CLASS H. At maximum scroll, no text may come to rest under the floating chrome or inside its fade. |

`lib.mjs` holds the shared state list: every screen, sheet, role and error state
worth auditing. A probe that iterates `states()` covers all 29.

Findings and their rulings: `.claude/plans/family-mockup4.md`.

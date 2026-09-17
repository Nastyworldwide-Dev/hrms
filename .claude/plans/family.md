# FAMILY — a decorative layer painted ON TOP of the text it decorates

CLASS: a full-bleed `position: absolute; inset: 0` pseudo-element with no
z-index. A positioned element whose `z-index` is `auto` paints in the
positioned-descendants layer — ABOVE the in-flow, unpositioned content of the
same box. Every cell, number and label on a glass panel is in-flow and
unpositioned, so the §6 gloss was washed over them: up to 55% white
(`--g-sheen`, light mode) at the panel's top-left, fading out by 40% across it.
The FIRST tile of every glass panel lost contrast; the rest kept it.

Reported 17 Sep 2026 by an employee about her own leave balance — "annual leave
tu nape dia mcm samar samar" — which is exactly the top-left tile.

ROOT CAUSE: `frontend/src/theme/glass-components.css`, `.g-glass::after`.
Fixed there: the panel isolates, the gloss sits at z-index -1 — above the
panel's own fill, below everything written on it.

NOT A DATA DEFECT. The numbers were right the whole time; only the first one
was unreadable.

## Every full-bleed pseudo-overlay in the stylesheet

frontend/src/theme/glass-components.css:332 (`.g-glass::after`) — same-root (fixed here)
  The reported symptom. One rule, every glass panel in the app.
frontend/src/theme/glass-components.css:333 (`.g-glass-ghost::after`) — same-root (fixed here)
  The same declaration block; the ghost variant had the identical bug.
frontend/src/theme/glass-components.css:830 (`.g-skeleton::after`) — not-affected
  The loading shimmer. A skeleton is a placeholder shape and never holds text,
  so an overlay above it covers nothing legible. Exempt in the new gate, by name.
frontend/src/theme/glass-components.css:48 (`.g-lightfield`) — not-affected
  The page-level twin, and the precedent: it was already given `z-index: 0`
  with `.g-page ion-content` lifted to `z-index: 1`. The panel-level layer was
  simply never wired the same way.

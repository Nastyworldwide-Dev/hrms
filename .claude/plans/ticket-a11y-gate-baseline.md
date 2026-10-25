# Ticket: a11y gate has no baseline, 216 "new" findings every run
Found 25 Oct 2026 (bug hunt). design/gates/a11y.mjs reports baseline allows 0 on every screen.
Fixed this session: aria-dialog-name (f66d74dfb), must-read scroll region.
Left: target-size on 44x44 header buttons and tab buttons (likely axe counting overlap, 44 is the floor), scrollable-region-focusable on team/sop/shift-requests (1 node each), meta-viewport (zoom disabled: an owner/iOS decision).
Next: rerun the gate after the two fixes, trace the remaining serious ones per screen, then record a baseline so new breaks show.

GOAL: sheets hold still and their scroll stops at their own edge
DONE WHEN: sheet-shift-audit: every reachable sheet 0 shifts, 0 extra, overscroll contain
CHECK: cd frontend && node e2e/sheet-shift-audit.mjs

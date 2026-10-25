# Ticket: drawn controls in Windows high contrast (forced-colors)
Found: design review of a68b4dcb5, 25 Oct 2026. No `@media (forced-colors: active)` rule exists in frontend/src except GCheckbox's.
Check: the drawn GSwitch fallback (.g-switch--drawn), GProgressRing, segment controls, lime pills — do they keep their state when Windows maps colours to system ones?
How to check: Chromium devtools > Rendering > Emulate CSS forced-colors: active, on /more (switches), /approvals, /home.

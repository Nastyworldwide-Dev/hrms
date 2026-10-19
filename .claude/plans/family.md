CLASS: the keyboard focus ring (:focus-visible) drawn after pointer use — browsers match it after ANY key (Escape) and on script focus (sheet open, focus returned to opener)
frontend/src/theme/glass-components.css same-root — one html[data-input="pointer"] rule hides every ring; covers all 18 :focus-visible rules incl. parent-drawn switch track and time-slip row
frontend/src/utils/focusModality.js same-root — sets data-input from pointerdown / navigation keys
frontend/src/components/glass/GModal.vue same-root — its sheet.focus() on open and opener.focus() on close were the script focus that drew the ring; behaviour kept (WAI-ARIA), ring now hidden after a tap
frontend/src/views/kpi/Dashboard.vue not-affected — .kpi-filter:focus-visible sets border only, ring comes from .g-focusable (covered)
frontend/src/components/TimeSlipFields.vue same-root — .timeslip-file:has(input:focus-visible) ring listed in the rule

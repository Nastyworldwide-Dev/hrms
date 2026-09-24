CLASS: native temporal input keeps WebKit's native appearance, so iOS Safari sizes it from its content and ignores width:100% (page drags sideways)

Instance: Time off form (from/to date) could be dragged sideways on the owner's iPhone, 24 Sep 2026.

Temporal inputs in the app (all now covered by ONE global rule in theme/glass-components.css):
- frontend/src/components/glass/GDatePicker.vue (type=date) — same-root
- frontend/src/components/glass/GDateTimePicker.vue (type=datetime-local) — same-root
- frontend/src/components/FormField.vue Time branch (type=time; Fix a day in/out time) — same-root
- any future input[type=date|time|datetime-local|month] — same-root (rule is by type, not by component)

Locked: theme/__tests__/temporal-inputs-fit.test.js (4 types). Verified in Chromium at 320px, light+dark: fields 288px wide, scrollWidth 320. Real-device check after deploy (WebKit cannot run on this machine).

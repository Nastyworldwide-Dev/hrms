CLASS: a vendor base style (frappe-ui Tailwind forms plugin) overriding a native control

Instance: owner's iPhone, iOS 26 — You page "Notifications" / "Shift reminders" drawn as blue checkboxes: [type=checkbox] { appearance: none; blue tick } stripped Safari's <input switch>.

Sites:
- frontend/src/theme/glass-components.css .g-switch__input — same-root (appearance auto, no background)
- GCheckbox (a real checkbox) — not-affected: it is meant to be a checkbox
- native <select> (GSelect) — not-affected: the plugin's select rule is overridden by .g-select__native (appearance none, our chevron) on purpose
- date/time inputs — not-affected: .g-datefield rules set their own appearance

Locked: native-controls.test.js (+1).

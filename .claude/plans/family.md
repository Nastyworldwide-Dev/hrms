CLASS: a control <input> (checkbox/radio/range/file/button) treated as a text field by the focus-ring rule
frontend/src/utils/focusModality.js same-root — isTextEntry limited to text-like inputs; Space on a switch is keyboard use
frontend/src/theme/glass-components.css same-root — the hide rule keeps the ring only on text-like inputs; switches hide it after a tap like buttons
frontend/src/components/glass/GCheckbox.vue not-affected — input type=checkbox, now treated as a control (covered by the rule)
frontend/src/components/TimeSlipFields.vue not-affected — input type=file, a control; its row ring stays in the rule

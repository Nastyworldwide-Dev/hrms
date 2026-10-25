CLASS: a Glass control styled at one class loses to the Tailwind forms plugin's [type="checkbox"] rules (same or higher specificity, loaded later), so the browser/plugin look shows through
frontend/src/theme/glass-components.css .g-check__box same-root — fixed: rules scoped .g-check .g-check__box, appearance none, drawn lime box + on-brand tick, focus ring only on keyboard
frontend/src/components/glass/GCheckbox.vue users (MustReadNotice, announcements/Detail, Approvals select-all, FormattedField Check fields) same-root — all render .g-check, all get the fix
frontend/src/theme/glass-components.css GSwitch native (.g-switch input, accent-color) not-affected — native switch on purpose (alpha.7 B17), appearance auto
frontend/src/components/ExpenseTaxesTable.vue not-affected — only excludes checkboxes from an input rule; no checkbox rendered

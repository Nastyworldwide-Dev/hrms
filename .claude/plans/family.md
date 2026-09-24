CLASS: a native <select> that always has a value still drew an empty first <option> (iOS shows it as a blank menu slot)

Instance: plan §2 0.7 — Profile > Appearance menu, a blank slot above "Light".

Sites:
- frontend/src/components/glass/GSelect.vue — same-root (empty option only with a placeholder or while unset)
- frontend/src/views/Profile.vue Appearance — same-root (always has a mode; now no blank slot)
- frontend/src/components/FormField.vue Select rows — not-affected: an unset form field still gets its empty option; a set one no longer offers "" (Frappe Select with a leading "\n" still lists "" as its own option)
- frontend/src/components/ListFiltersActionSheet.vue — not-affected: passes placeholder "All", so the empty option stays and reads "All"
- the menu's look (glass, position) — not-affected: it is iOS's own native picker; not ours to draw

Locked: native-controls.test.js (+1).

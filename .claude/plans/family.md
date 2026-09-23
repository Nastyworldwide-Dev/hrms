CLASS: a sheet noted the page it belongs to too late (willPresent), after a quick Back had already landed.

Call sites: frontend/src/components/glass/GModal.vue openedOn — same-root, fixed (noted when isOpen turns true; willPresent falls back for trigger-opened sheets; cleared on didDismiss). frontend/src/router/sheetGuard.js — not-affected (closes presented sheets; the mid-present case is GModal's by design).

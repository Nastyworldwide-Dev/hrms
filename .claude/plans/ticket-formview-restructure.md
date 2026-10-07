# Ticket: FormView restructure (menu, dialog, errors)

STATUS: DONE 2026-10-07, commit pending (slice S4 of the alpha.41 plan).

History: FormView used frappe-ui Dropdown, Dialog and ErrorMessage. The Dropdown
rendered headlessui MenuButton as a div with disabled="false" (axe
aria-allowed-attr, critical, on every request detail screen).

- The ... menu is a GActionSheet and the cancel/delete dialogs are GConfirm
  (alpha.7 Phase 4; pinned by components/__tests__/cancel-confirm-glass.test.js).
- 2026-10-07: the last one, the form's error line, is now FormField's Glass
  `.g-field-error` line with role="alert" (plain text through firstMessage, no
  v-html). The allow-list entry in tests/audit/no-frappe-ui-controls.test.mjs is
  gone (ALLOW_LIST is empty) and design/a11y-baseline.json is `{}`, so there were
  no FormView baseline entries left to drop.
- The global Button registration in main.js is already gone (comment at main.js L71).
- Left for another slice: tailwind.config.js still scans frappe-ui ErrorMessage.vue (pinned by src/__tests__/first-download.test.js); nothing renders it now.

Upgrade trigger: none. Reopen only if FormView grows a new frappe-ui control; the
audit test fails on it.

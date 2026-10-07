# Ticket: FormView restructure (menu, dialog, errors)

FormView still uses frappe-ui Dropdown, Dialog and ErrorMessage (allow-listed in
tests/audit/no-frappe-ui-controls.test.mjs). The Dropdown renders headlessui
MenuButton as a div with disabled="false": axe aria-allowed-attr (critical) on
every request detail screen, baselined in design/a11y-baseline.json.

Do: the ... menu as a GActionSheet; the cancel/delete dialogs as GConfirm;
field errors as the Glass error line. Then drop the allow-list entry, the five
baseline entries and the global Button registration in main.js.

Upgrade trigger: any change to FormView header or dialogs.

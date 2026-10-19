CLASS: a time field's starting value is a fixed clock time that can fall outside the field's own min/max, so the sheet opens invalid with its submit off
frontend/src/components/LateCheckoutDialog.vue same-root — 18:00 default fell before a check-in after 18:00; now defaultCheckoutTime (clamped to IN+1min and now)
frontend/src/components/CheckInPanel.vue not-affected — opens the dialog; picks no time
frontend/src/components/FormField.vue not-affected — time/datetime fields start from the doctype default or empty, no min/max set
frontend/src/components/glass/GDateTimePicker.vue not-affected — no default of its own; value comes from the caller

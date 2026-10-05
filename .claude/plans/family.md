CLASS: a list that hides the chosen record while the user types, when the control draws its CLOSED text from that same list. frappe-ui's Autocomplete finds the chosen option in the options it is given; a typed search that dropped the chosen shift left the box behind the popover blank (design review of 3a860c31e). Before the picker fixes the chosen record was always kept in the list.
roster/src/components/Link.vue:shownOptions same-root (fixed here: the chosen record is always in the list, with its looked-up label)
roster/src/components/Link.vue:options.onSuccess same-root (fixed here: looks the label up whenever the record is outside the loaded page and not already known, typed or not)
roster/src/components/ShiftAssignmentDialog.vue:Link x3 same-root — all three pickers use Link.vue
frontend/src/components/Link.vue not-affected — the Nadi picker draws its trigger from modelValue and the loaded options, never hides the chosen one

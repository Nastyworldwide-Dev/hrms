CLASS: a fix that changes what a picker opens with can change what its trigger SAYS. Opening on the full list (1c63f546b) stopped looking up the chosen record, so a chosen person past the first page would read as a bare id ("HR-EMP-00012"), not "W0 foreign : HR-EMP-00012" (Frappe review). The chosen option also had no tick in a long list, and 50 rows plus the chosen one hid the last real row (design review).
roster/src/components/Link.vue same-root (fixed here: the chosen record's own label is looked up once when it is outside the first page; a tick marks the chosen option; 49 rows, not 50)
roster/src/components/ShiftAssignmentDialog.vue:Link x3 same-root — Employee, Shift Type and Shift Location all use Link.vue, so all three get it
frontend/src/components/Link.vue not-affected — the Nadi picker is a separate component with its own sheet and selected tick
roster/src/components/MonthViewHeader.vue not-affected — filters use createListResource of names, no search_link

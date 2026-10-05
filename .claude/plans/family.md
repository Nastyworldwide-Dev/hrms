CLASS: a picker that opens by SEARCHING for the value already chosen. search_link is a "contains" search, so a person on "Day Shift" got only the shifts whose name contains "Day Shift" (2 of 25 on the test site), and every other shift vanished from the list HR was meant to choose from.
roster/src/components/Link.vue:onMounted same-root (fixed here: opens on the full list; the chosen record is kept in it; first page 50, not 10)
roster/src/components/ShiftAssignmentDialog.vue:Link x3 same-root — the three pickers (Shift Type, Shift Location, Employee-side) all use Link.vue, so all are fixed at once
frontend/src/components/Link.vue not-affected — the Nadi picker opens with reloadOptions("") already and injects the chosen record
roster/src/components/MonthViewHeader.vue not-affected — its filters use createListResource of all names (pageLength 100), not a search
hrms/api/roster.py:get_shifts not-affected — returns assignments, the picker's list never comes from it

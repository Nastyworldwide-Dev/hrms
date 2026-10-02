GOAL: HR can change a shift on the Desk Roster (screenshot: Update greyed, fields locked).
DONE WHEN: Shift Type / Location / End Date editable on an existing shift; a type/location change updates that day via change_shift_day; HR User can do it on a first day.
CHECK: node --test roster/src/components/__tests__/ShiftAssignmentDialog.test.js; fresh.local console test_roster 13/13.

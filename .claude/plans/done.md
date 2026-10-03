GOAL: Fahmie (Shift Supervisor) can delete and update shifts on the Desk Roster (screenshot: "does not have doctype access via role permission for document Shift Assignment").
DONE WHEN: Delete -> All Consecutive Shifts, Delete -> Shift Schedule Assignment and Update work for a supervisor's own team and are refused for a stranger; no roster screen writes through frappe.client.
CHECK: fresh.local console test_roster 21/21; node --test roster/src/components/__tests__/ShiftAssignmentDialog.test.js

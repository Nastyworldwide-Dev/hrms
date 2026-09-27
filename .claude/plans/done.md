GOAL: no view reads employee.data.<field> while the page is set up (the rest of cdd790d4c's class).
DONE WHEN: ShiftRequestForm, leave Form, expense claim Form, IssueList guarded; a test walks every view's setup lines.
CHECK: node --test frontend/src/views/__tests__/you-without-employee.test.js (red with the old leave Form line, green now)

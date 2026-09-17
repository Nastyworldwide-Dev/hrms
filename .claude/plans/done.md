GOAL: The check-in button stops reading "Check In" to somebody who is checked in.
DONE WHEN: lastLog falls back to the last delivered row during a reload instead
 of {}, so liveAction never reads a reload as "no open session".
CHECK: cd frontend && node --experimental-test-module-mocks --test
 src/components/__tests__/CheckInPanel.test.js
 src/components/__tests__/CheckInPanel.location.test.js

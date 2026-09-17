GOAL: The two things the re-review asked to be written down, are written down.
DONE WHEN: lastKnownLog carries a ceiling marker with an upgrade trigger for the
 out-of-order reload, and says it can transiently be a partial punch row.
CHECK: cd frontend && node --experimental-test-module-mocks --test
 src/components/__tests__/CheckInPanel.test.js
 src/components/__tests__/CheckInPanel.location.test.js

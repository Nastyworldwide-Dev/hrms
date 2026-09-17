GOAL: The two selfie-timing tests drive the upload where it actually happens.
DONE WHEN: the location suite holds the upload open through the
 hrms.api.remote_checkin.upload_selfie resource, and is green with no
 pre-existing failures left.
CHECK: cd frontend && node --experimental-test-module-mocks --test
 src/components/__tests__/CheckInPanel.location.test.js

GOAL: the bell and the notification feed are never left stale
DONE WHEN: they reload after a socket gap (reconnect / back after a long hide) and when a push lands while the app is open
CHECK: node --test frontend/src/data/__tests__/notifications-catch-up.test.js frontend/tests/personal-cache-isolation.test.mjs

GOAL: tapping a Nadi push notification always opens its page, even when push messaging failed to start in the worker.
DONE WHEN: the notificationclick handler sits outside the Firebase try block, waits with event.waitUntil, and reuses an open Nadi window; sw tests red before, green after; build OK.
CHECK: node --test frontend/src/__tests__/sw.test.js

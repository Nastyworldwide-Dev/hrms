GOAL: the lime focus ring shows only for keyboard movement, never after a tap (owner, 19 Oct 2026)
DONE WHEN: focusModality.test.js red on HEAD, green now; WebKit + Chromium: no ring after tap-open or tap-then-Escape, ring after Tab
CHECK: node --test frontend/src/utils/__tests__/focusModality.test.js

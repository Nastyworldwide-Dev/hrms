GOAL: switches and checkboxes behave like buttons for the focus ring; only text boxes keep theirs after a tap
DONE WHEN: focusModality.test.js switch cases red on HEAD, green now; WebKit + Chromium tap-a-switch-then-Escape shows no ring
CHECK: node --test frontend/src/utils/__tests__/focusModality.test.js

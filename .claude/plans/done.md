GOAL: keyboard users keep the focus ring after a tap; text fields keep theirs (design review of the focus fix)
DONE WHEN: focusModality.test.js new cases red on HEAD, green now; WebKit tap-then-Enter shows the ring; tap and Escape still show none
CHECK: node --test frontend/src/utils/__tests__/focusModality.test.js

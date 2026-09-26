GOAL: the app never opens to a blank white screen; a launch shell paints before any script
DONE WHEN: with scripts held back 3 s, the shell is visible at 500 ms in light and dark; Vue replaces it on mount
CHECK: cd frontend && node --test src/__tests__/boot-shell.test.js

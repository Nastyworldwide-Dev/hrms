GOAL: the app's appearance follows the phone; no in-app Light/Dark picker
DONE WHEN: Profile has no Appearance row; a stored Light/Dark is cleared; pre-paint and runtime both read the system setting
CHECK: cd frontend && node --test src/data/__tests__/theme-follows-the-phone.test.js

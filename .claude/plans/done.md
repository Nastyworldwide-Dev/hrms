GOAL: the Calendar says the month in one line — days worked, and how many to fix, tappable
DONE WHEN: live W0 September reads "2 days worked" (2 Present + 1 On Leave in the data); "to fix" opens the first such day
CHECK: cd frontend && node --test src/utils/__tests__/monthSummary.test.js

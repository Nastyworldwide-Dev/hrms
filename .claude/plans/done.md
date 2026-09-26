GOAL: the Today card shows the shift the Apple way: a labelled gauge, a breathing working dot, a rolling time, a drawn tick on save, and a forgot-to-check-out prompt
DONE WHEN: live on the bench at 13:47 a 09:00-18:00 shift shows "4h 13m left" at 53%; tests + motion + lint gates green
CHECK: cd frontend && node --test src/utils/__tests__/shiftGauge.test.js src/components/__tests__/today-card-apple-way.test.js

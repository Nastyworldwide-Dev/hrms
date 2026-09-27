GOAL: a sent leave request no longer shows a stale "Days left before this 19"; the balance shows while writing, as "Days left".
DONE WHEN: leave_balance only in FIELDS_ON_NEW; plainLabel reads "Days left".
CHECK: node --test frontend/src/views/__tests__/leave-balance-while-writing.test.js; WebKit decided leave: daysLeft false

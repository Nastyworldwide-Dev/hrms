GOAL: "Couldn't load your leave" is announced to screen readers and "pull down to try again" really reloads the balances.
DONE WHEN: the row carries role="status"; Requests pull-to-refresh reloads requestsSummary; test red before, green after.
CHECK: node --test frontend/src/components/__tests__/request-balances.test.js

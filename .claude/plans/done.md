GOAL: a failed load says "Could not load … Try again", never "No … yet"
DONE WHEN: forced-500 run shows the error with Try again on the lists and Profile; tests red before, green after
CHECK: cd frontend && node --test src/components/__tests__/list-failure-is-not-empty.test.js

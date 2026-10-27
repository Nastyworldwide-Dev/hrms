GOAL: the remembered placeholder heights never hold a stale size (review of bcfbeaa8e/d612c8d07).
DONE WHEN: an emptied Needs you forgets its height; an expanded Approvals group is not remembered; logout removes every hrms:ph: key.
CHECK: node --test frontend/src/utils/__tests__/placeholderHeight.test.js frontend/tests/personal-cache-isolation.test.mjs

GOAL: Who to ask always refreshes HR contacts when opened, so a change or a failed read is seen.
DONE WHEN: WhoToAsk reloads on mount instead of skipping when cached.
CHECK: node --test frontend/src/components/__tests__/WhoToAsk.test.js; /hr-contacts forced-500 5/5 Try again (was 1 miss in 3)

GOAL: every empty list says what is true in one voice ("No <things> yet" + a short line saying what to do) and offers New itself when you can add.
DONE WHEN: ListView EMPTY_COPY rewritten; GEmptyState action slot carries New when canCreate; RequestList/Leave dashboard fallbacks match.
CHECK: node --test frontend/src/components/__tests__/empty-lists-one-voice.test.js; yarn test all green

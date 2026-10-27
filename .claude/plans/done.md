GOAL: Approvals and Home "Needs you" hold their last answered height while loading, so the content below stops jumping (design audit 27 Oct, finding 1).
DONE WHEN: on a return visit the "already answered" panel and "Your week" do not move; a first-ever visit may move once; private mode still renders.
CHECK: node --test frontend/src/utils/__tests__/placeholderHeight.test.js; PASS=warm node frontend/e2e/scroll-and-shift-audit.mjs (Home, Approvals not listed).

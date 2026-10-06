CLASS: test and repo hygiene that hid real signals. A test pinned the QUOTE STYLE of a template attribute and went red when the quotes changed, so the components suite carried one permanent red that made new reds easy to miss; and the crawl's raw output file sat untracked in every `git status`. 14 throw-away probe scripts of 6 Oct (frontend/e2e/live-*.mjs, untracked) were deleted; their findings are in progress.md and the two e2e gates.
frontend/src/components/__tests__/no-jump-placeholders.test.js same-root (fixed here: asserts the words on one GListRow in either quote style; still fails when the words change)
frontend/.gitignore same-root (fixed here: e2e/.audit-crawl.json is a run artifact)
frontend/src/views/Approvals.vue not-affected — unchanged; the test now reads it as written

CLASS: a fix proven only by a test that reads the source. The behaviour (a real pull-down makes the screen reload; a real scroll loads more) is now pinned by two real-browser specs that drag and scroll with touch events on the running app and fail with the old listener (pull: 4 of 4 red; scroll: red) and pass with the fix. They run with `yarn test:e2e` against the test site, not in the commit gate (the gate runs spec files with bun, which cannot run Playwright).
frontend/e2e/pull-refresh.spec.js same-root (new: real touch pull on Home, Requests, Approvals, Announcements; the handler runs once and the data requests go out)
frontend/e2e/list-scroll.spec.js same-root (new: a real scroll on the Leave list reaches the list's scroll handler)
frontend/src/components/glass/GPullRefresh.vue not-affected — fixed in 6253bdc45
frontend/src/components/ListView.vue not-affected — fixed in 6253bdc45
frontend/e2e/README.md ticket e2e-readme — lists the specs by the incident each catches; add these two

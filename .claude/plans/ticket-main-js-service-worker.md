# TICKET — frontend/src/main.js is a hotspot (28 commits / 90 days)

Raised by the review of b0811eab8 (28 Sep 2026). The service-worker block
(registration, the relay push-config cache, retiring the pre-alpha.12 worker,
moving push to the app worker) lives in main.js beside unrelated app boot. Every
update-bar fix this month has touched it: b2f020a62, 6621d7bd9, b0811eab8.

Proposal: move the block into src/utils/serviceWorker.js (registerAppWorker),
the way workerURL.js and data/swRegistration.js were split out; main.js calls
one function. Behaviour-neutral; covered by UpdatePrompt.one-worker.test.js,
workerURL.test.js and the live relay-flip probe.

Also noted by that review: workerURL's key sort keeps `undefined` values, so a
relay that sometimes omits a key and sometimes sends it undefined would still
give two addresses. Not the Firebase config shape today; revisit if it changes.

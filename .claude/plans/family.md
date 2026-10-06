CLASS: a submit made offline told people "Failed to fetch" (or nothing) and a second "Something didn't load" toast; owner ruling R4 (6 Oct): a clear failure, no queue.
frontend/src/utils/loudRequest.js:firstMessage same-root (a network failure with no server answer -> "You are offline. Nothing was sent and your form is kept."; the one reader every form uses, 27 call sites)
frontend/src/utils/loudRequest.js:makeLoudRequest same-root (no generic toast on top of an offline failure; the offline banner already shows the state)
frontend/src/components/OfflineBanner.vue not-affected — already says "No connection. Anything you send now will not reach us."
frontend/src/components/CheckInPanel.vue not-affected — owner ruling 22 Sep: never an offline check-in; its own message stands

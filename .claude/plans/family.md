CLASS: a cached list never re-read on open, so a failure (or a change) is never seen
frontend/src/components/WhoToAsk.vue:59 same-root — reload on open; the saved list still shows at once
frontend/src/data/hrContacts.js:4 not-affected — the resource definition (auto: false, cached)

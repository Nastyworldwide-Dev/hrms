CLASS: per-user data left in browser storage after the user changes (shared-phone leak; same class as audit P0-5, the idb document cache)
frontend/src/data/session.js:44 same-root — logout now clears the page copy
frontend/src/data/session.js:16 same-root — login clears it too (an expired session never passed through logout)
frontend/public/sw.js:39 not-affected — the writer; NetworkFirst stays for offline opening
frontend/src/utils/personalCache.js:88 not-affected — clears IndexedDB keys, already covered

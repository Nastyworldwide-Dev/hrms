CLASS: a page that reloads to recover from a refusal the reload cannot fix (loop), and a reload that races the cleanup it depends on.
frontend/src/utils/personalCache.js:sessionEnded same-root (one reload per still-signed-in cookie, then stay; reload waits for the page-copy clear, capped 2 s)
frontend/src/router/navigationGate.js not-affected — calls sessionEnded; a false answer now keeps the navigation where it is instead of looping
frontend/src/data/user.js, employee.js, employees.js not-affected — call sessionEnded once; the cap is inside it
frontend/src/data/session.js:logout not-affected — its own reload after an awaited clearCachedPages

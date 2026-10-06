# Ticket: one owner for "the session ended" (frontend)

Opened 6 Oct 2026 (alpha.36 D2). Refactor ticket, not scheduled.

## Why
frontend/src/data/session.js had 5 fixes in 90 days and frontend/src/utils/personalCache.js 3.
Files that keep needing fixes carry the next bug.

## What is spread today
"The session ended, go to Login" is decided in five places:
- utils/personalCache.js `sessionIsCurrent()`: cookie or epoch changed -> hide page, reload, leave the
  "signed out" mark (alpha.35).
- resourceConfig.js `guestQuiet`: Guest cookie -> hold the request forever (never resolves).
- router/navigationGate.js: user read fails as logged out -> route to Login.
- data/user.js and data/employees.js `onError`: AuthenticationError -> router.push Login (no reload, no mark).
- data/session.js `logout`: clears caches, marks logging out, reloads.

Each is right on its own; together a new path can forget one step (the mark, the cache clear, the reload).
The alpha.35 review warned that the user.js/employees.js path skips the mark (unproven live: the reload in
sessionIsCurrent arrives first).

## Proposed shape (when picked up)
One function, e.g. `sessionEnded(why)` in personalCache.js, that every path calls: mark (unless logging out),
clear the offline page copy, reload. The five sites call it instead of routing on their own.

## Done when
- grep finds `name: "Login"` only in the router itself and in sessionEnded.
- A test per caller: AuthenticationError on user/employee read -> sessionEnded called once.
- Live: expire a session, tap anything -> Login with the banner (the alpha.35 probe).

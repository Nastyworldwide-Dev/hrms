CLASS: a session that ends on its own (expired, signed out elsewhere) reloads the page onto Login with nothing said. sessionIsCurrent() sees the Guest cookie and reloads; any message shown on the old page is lost with it, so a Submit after expiry looked like "nothing happened" (AU-2).
frontend/src/utils/personalCache.js:sessionIsCurrent same-root (the one place every request and focus/visibility check routes through when a session ends; leaves a one-shot sessionStorage mark only when this page HAD a user, now has none, and it is not a Log out)
frontend/src/data/session.js:logout same-root (markLoggingOut before the logout call, so a deliberate Log out says nothing)
frontend/src/views/Login.vue same-root (reads the mark once, shows "You were signed out. Sign in again to continue.")
frontend/src/router/navigationGate.js not-affected — sends a Guest to Login; the reload from sessionIsCurrent arrives first and has already left the mark
frontend/src/data/user.js, frontend/src/data/employees.js not-affected — push Login on AuthenticationError; same page, same reload path
frontend/src/utils/loudRequest.js not-affected — the earlier in-page notice draft was dropped: the reload hides it (proved live 6 Oct)

CLASS: "the session ended" decided in several places, each doing some of the steps (signed-out mark, offline page copy, reload) and forgetting the rest (ticket docs/glass/tickets/2026-10-06-session-identity-hotspot.md).
frontend/src/utils/personalCache.js same-root (sessionEnded(): the one owner, once per page; sessionIsCurrent routes through it)
frontend/src/data/user.js, employee.js, employees.js same-root (AuthenticationError -> sessionEnded, no router.push Login)
frontend/src/router/navigationGate.js + main.js same-root (a page that HAD a user calls sessionEnded; a page that never had one still gets {name:"Login"})
frontend/src/views/Login.vue same-root (no longer clears pages itself; sessionEnded did)
frontend/src/data/session.js:logout not-affected — Log out is the person's own act: its own reload, no signed-out mark (markLoggingOut)

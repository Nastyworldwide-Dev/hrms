CLASS: a "logging out" flag that outlives a failed Log out, so a later real session end is taken for a deliberate one and the "signed out" banner is never shown.
frontend/src/utils/personalCache.js same-root (clearLoggingOut beside markLoggingOut; the flag has one owner)
frontend/src/data/session.js:logout same-root (onError clears the flag)
frontend/src/data/session.js:login/otp not-affected — never set the flag
frontend/src/data/user.js, employees.js, router/navigationGate.js ticket docs/glass/tickets/2026-10-06-session-identity-hotspot.md — five places decide "session ended"; one owner proposed there

CLASS: the last person's offline page copy outlives a session that ended on its own (AU-5): it is cleared on login and logout only.
frontend/src/views/Login.vue same-root (clears it when the "signed out" banner shows, the one place that knows the session ended on its own)
frontend/src/data/session.js:handleLogin, logout not-affected — already clear it
frontend/public/sw.js not-affected — serves the copy; clearing it is the app's job

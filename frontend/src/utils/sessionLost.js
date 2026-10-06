// Does this failure mean the person is no longer logged in?
//
// Only when the SERVER says so: a 401/403 reply, or an authentication /
// session-expired exception. A failure with no reply at all — offline, a
// timeout, a dropped connection — says nothing about the session, and until
// 23 Sep the router treated it as a logout: changing page with no signal threw
// people onto the Login screen (audit P0-6).
const LOGGED_OUT_TYPES = new Set([
	"AuthenticationError",
	"SessionExpired",
	"PermissionError:Guest",
])

export function isSessionLost(error) {
	if (!error) return false
	const status = error.response?.status
	if (status === 401 || status === 403) return true
	if (LOGGED_OUT_TYPES.has(error.exc_type)) return true
	return false
}

// Is this a refusal of THIS page, from a person who is still signed in?
//
// isSessionLost() above answers a different question and says yes to every
// 403, because a 403 on the user read means the session is gone. For a detail
// screen the same 403 usually means "this record is not yours to open": the
// cookie still names the person. So no-access is a 403 / PermissionError only
// while the person is signed in and the server did not say the session ended
// (AuthenticationError, SessionExpired, a Guest PermissionError, a 401). A
// session that really ended is answered by the reload onto Login, never by a
// sentence on this page.
export function isNoAccess(error, { signedIn }) {
	if (!error || !signedIn) return false
	if (LOGGED_OUT_TYPES.has(error.exc_type)) return false
	const status = error.response?.status
	if (status === 401) return false
	return status === 403 || error.exc_type === "PermissionError"
}

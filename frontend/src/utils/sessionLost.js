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

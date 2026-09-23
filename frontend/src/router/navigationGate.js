// Where a navigation may go, decided from who is logged in and which employee
// they are. Extracted from main.js's router guard so it can be tested — that
// guard had needed four fixes in 90 days.
//
// Only the SERVER can end a session or reject an identity. A failure to reach
// it is neither: offline, the user re-check threw people onto Login (audit
// P0-6), and once that was fixed the employee check — awaiting a promise that
// had already failed — threw inside the guard and froze every navigation
// (review of 9fb28a77b). Both reads now answer "unknown" on a network failure,
// and unknown lets the person carry on with what the app already holds.
import { isSessionLost } from "../utils/sessionLost.js"

// Returns what vue-router's guard should return: undefined (go ahead), false
// (stay), or a location to redirect to.
export async function decideNavigation({
	to,
	session,
	userResource,
	employeeResource,
	employeeGate,
}) {
	let isLoggedIn = session.isLoggedIn
	if (isLoggedIn) {
		const lost = await sessionEndedDuring(() => userResource.reload())
		if (lost) isLoggedIn = false
	}

	if (!isLoggedIn) {
		// password reset page is outside the PWA scope
		if (to.path === "/update-password") return false
		return to.name === "Login" ? undefined : { name: "Login" }
	}

	if (await sessionEndedDuring(() => employeeResource.promise)) return { name: "Login" }

	// No employee in hand (offline before the first read ever landed): no
	// identity verdict is possible, so none is given.
	if (!employeeResource.data) {
		console.warn("[navigationGate] employee unknown; letting the navigation through")
		return undefined
	}
	// user should be an employee to access the app since all views are
	// employee specific — and a valid employee is never kept on the failure
	// page. The decision (logins compared normalized) is utils/identity.js.
	return (
		employeeGate({ to: to.name, employee: employeeResource.data, user: userResource.data }) ||
		undefined
	)
}

//: Run a read; true only when the server said the session is over. Any other
//: failure (offline, a timeout, a 500) is logged and treated as "still in".
async function sessionEndedDuring(read) {
	try {
		await read()
		return false
	} catch (error) {
		if (isSessionLost(error)) return true
		console.warn(
			"[navigationGate] could not reach the server; keeping the session",
			error?.message
		)
		return false
	}
}

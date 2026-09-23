// Every navigation re-checks who is logged in and which employee they are.
// A failure to REACH the server is never a verdict on either: offline, the
// user check threw people onto Login (P0-6), and once that was fixed the
// employee check, awaiting a promise that had already failed, threw inside
// the guard and froze every navigation (review of 9fb28a77b).
import { test } from "node:test"
import assert from "node:assert/strict"

import { decideNavigation } from "../navigationGate.js"

const offline = () => Promise.reject(new TypeError("Failed to fetch"))
const expired = () =>
	Promise.reject(
		Object.assign(new Error("x"), { response: { status: 403 }, exc_type: "PermissionError" })
	)

function world({
	loggedIn = true,
	userReload = async () => {},
	employeePromise = Promise.resolve(),
	employee = { user_id: "a@x" },
} = {}) {
	employeePromise.catch(() => {})
	return {
		session: { isLoggedIn: loggedIn },
		userResource: { reload: userReload, data: { name: "a@x" } },
		employeeResource: { promise: employeePromise, data: employee },
		employeeGate: ({ employee: e, user }) =>
			e && e.user_id === user.name ? null : { name: "InvalidEmployee" },
	}
}

test("offline, with the employee already known: the navigation goes ahead", async () => {
	const out = await decideNavigation({
		to: { name: "Requests", path: "/requests" },
		...world({ userReload: offline, employeePromise: offline() }),
	})
	assert.equal(out, undefined)
})

test("offline, with no employee loaded yet: no identity verdict, the navigation goes ahead", async () => {
	const out = await decideNavigation({
		to: { name: "Requests", path: "/requests" },
		...world({ userReload: offline, employeePromise: offline(), employee: null }),
	})
	assert.equal(out, undefined)
})

test("the server says the session ended: Login", async () => {
	const out = await decideNavigation({
		to: { name: "Requests", path: "/requests" },
		...world({ userReload: expired }),
	})
	assert.deepEqual(out, { name: "Login" })
})

test("the employee read says the session ended: Login", async () => {
	const out = await decideNavigation({
		to: { name: "Requests", path: "/requests" },
		...world({ employeePromise: expired() }),
	})
	assert.deepEqual(out, { name: "Login" })
})

test("online, a real mismatch still goes to InvalidEmployee", async () => {
	const out = await decideNavigation({
		to: { name: "Requests", path: "/requests" },
		...world({ employee: { user_id: "b@x" } }),
	})
	assert.deepEqual(out, { name: "InvalidEmployee" })
})

test("logged out: Login, and the reset page is left alone", async () => {
	assert.deepEqual(
		await decideNavigation({ to: { name: "Home", path: "/home" }, ...world({ loggedIn: false }) }),
		{ name: "Login" }
	)
	assert.equal(
		await decideNavigation({
			to: { name: "Login", path: "/login" },
			...world({ loggedIn: false }),
		}),
		undefined
	)
	assert.equal(
		await decideNavigation({
			to: { name: "X", path: "/update-password" },
			...world({ loggedIn: false }),
		}),
		false
	)
})

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

// sessionEnded is the ONE owner of "the session ended" (utils/personalCache.js, R1): the gate hands a
// lost session to it instead of routing to Login itself, so the signed-out mark and the offline page
// copy are never forgotten. A recorder stands in for it here.
function world({
	loggedIn = true,
	userReload = async () => {},
	employeePromise = Promise.resolve(),
	employee = { user_id: "a@x" },
} = {}) {
	employeePromise.catch(() => {})
	const ended = []
	return {
		ended,
		sessionEnded: () => (ended.push(1), true),
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

test("the server says the session ended: sessionEnded once, the page stays for the reload", async () => {
	const w = world({ userReload: expired })
	const out = await decideNavigation({ to: { name: "Requests", path: "/requests" }, ...w })
	assert.equal(w.ended.length, 1)
	assert.equal(out, false)
})

test("the employee read says the session ended: sessionEnded once, the page stays", async () => {
	const w = world({ employeePromise: expired() })
	const out = await decideNavigation({ to: { name: "Requests", path: "/requests" }, ...w })
	assert.equal(w.ended.length, 1)
	assert.equal(out, false)
})

test("offline: sessionEnded is never called", async () => {
	const w = world({ userReload: offline, employeePromise: offline() })
	await decideNavigation({ to: { name: "Requests", path: "/requests" }, ...w })
	assert.equal(w.ended.length, 0)
})

test("online, a real mismatch still goes to InvalidEmployee", async () => {
	const out = await decideNavigation({
		to: { name: "Requests", path: "/requests" },
		...world({ employee: { user_id: "b@x" } }),
	})
	assert.deepEqual(out, { name: "InvalidEmployee" })
})

test("logged out: Login, and the reset page is left alone", async () => {
	const w = world({ loggedIn: false })
	assert.deepEqual(await decideNavigation({ to: { name: "Home", path: "/home" }, ...w }), {
		name: "Login",
	})
	assert.equal(w.ended.length, 0, "a page that never had a user has no session to end")
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

test("main.js hands the guard the one owner, and no data module routes to Login on its own", async () => {
	const { readFileSync } = await import("node:fs")
	const read = (p) => readFileSync(new URL(p, import.meta.url), "utf8")
	const main = read("../../main.js")
	assert.match(main, /import \{[^}]*\bsessionEnded\b[^}]*\} from "@\/utils\/personalCache"|import \{ sessionEnded \} from "@\/utils\/personalCache"/)
	assert.match(main, /decideNavigation\(\{[^}]*\bsessionEnded\b[^}]*\}\)/)
})

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
	fetched = false,
	roles = [],
	isHr = false,
} = {}) {
	employeePromise.catch(() => {})
	const ended = []
	return {
		ended,
		sessionEnded: () => (ended.push(1), true),
		session: { isLoggedIn: loggedIn },
		userResource: { reload: userReload, data: { name: "a@x", roles, is_hr: isHr } },
		employeeResource: { promise: employeePromise, data: employee, fetched },
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
	assert.match(
		main,
		/import \{[^}]*\bsessionEnded\b[^}]*\} from "@\/utils\/personalCache"|import \{ sessionEnded \} from "@\/utils\/personalCache"/
	)
	assert.match(main, /decideNavigation\(\{[^}]*\bsessionEnded\b[^}]*\}\)/)
})

// Mia, 16 Oct 2026: the server ANSWERED and found no Employee for this login (it returns null).
// That is a verdict, not "unknown": she was let into Home and every read there 403'd.
test("the server found no employee: InvalidEmployee, not Home", async () => {
	const out = await decideNavigation({
		to: { name: "Home", path: "/home" },
		...world({ employee: null, fetched: true }),
	})
	assert.deepEqual(out, { name: "InvalidEmployee" })
})

test("no employee, already on the failure page: stays there", async () => {
	const out = await decideNavigation({
		to: { name: "InvalidEmployee", path: "/invalid-employee" },
		...world({ employee: null, fetched: true }),
	})
	assert.equal(out, undefined)
})

// An Attendance Report Viewer needs no Employee for what the role is for: Team (company view) and
// the Excel download read the role and Company User Permission only. She starts on More.
test("a viewer with no employee: Home sends her to More; More, Team and the download open", async () => {
	const viewer = () =>
		world({ employee: null, fetched: true, roles: ["Attendance Report Viewer"] })
	assert.deepEqual(await decideNavigation({ to: { name: "Home", path: "/home" }, ...viewer() }), {
		name: "MoreView",
	})
	assert.deepEqual(
		await decideNavigation({
			to: { name: "InvalidEmployee", path: "/invalid-employee" },
			...viewer(),
		}),
		{ name: "MoreView" }
	)
	for (const [name, path] of [
		["MoreView", "/more"],
		["TeamView", "/team"],
		["AttendanceDownload", "/attendance-download"],
		// the only Log out is on Profile (design review of 9ce8bcecb)
		["Profile", "/profile"],
		["Notifications", "/notifications"],
		["ChangePassword", "/change-password"],
	])
		assert.equal(await decideNavigation({ to: { name, path }, ...viewer() }), undefined, name)
})

// Review of 9ce8bcecb: an HR or admin login with no Employee was let in before; that rule is unchanged.
test("an HR login with no employee keeps the old pass", async () => {
	const out = await decideNavigation({
		to: { name: "Approvals", path: "/approvals" },
		...world({ employee: null, fetched: true, isHr: true }),
	})
	assert.equal(out, undefined)
})

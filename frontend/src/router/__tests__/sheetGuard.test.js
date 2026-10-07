// A sheet must never outlive the page that opened it. Ionic presents an
// inline ion-modal at the app root, so a Back or a tab switch left the sheet
// floating over the next page, its scrim stranded in the hidden page, and the
// tab bar untappable (audit P0-3, reproduced live 23 Sep).
import { test } from "node:test"
import assert from "node:assert/strict"

import { closeSheetsOnLeave } from "../sheetGuard.js"

// A router double with the three seams the guard uses: beforeEach, afterEach and
// the RouterHistory.listen that vue-router fires for a popstate. `pop(delta)` is a
// browser/Android Back (or Forward): the history listener fires first, then the
// navigation runs the guards, like vue-router's own popstate handler.
function fakeRouter() {
	const guards = []
	const afterEach = []
	const listeners = []
	const run = async (to, from) => {
		let result
		for (const guard of guards) {
			result = await guard(to, from)
			if (result !== undefined) break
		}
		return result
	}
	return {
		router: {
			beforeEach: (fn) => guards.push(fn),
			afterEach: (fn) => afterEach.push(fn),
			resolve: (to) => ({ fullPath: to }),
			options: { history: { listen: (fn) => listeners.push(fn) } },
		},
		navigate: async (to = { path: "/home" }, from = { path: "/dashboard/attendance" }) =>
			run(to, from),
		listen: (to, from, delta) => listeners.forEach((fn) => fn(to, from, { type: "pop", delta })),
		pop: async (
			delta,
			to = { path: "/home", fullPath: "/home" },
			from = { path: "/more", fullPath: "/more" }
		) => {
			listeners.forEach((fn) => fn(to.fullPath, from.fullPath, { type: "pop", delta }))
			return run(to, from)
		},
		// vue-router's afterEach: lands, aborts or is cancelled
		settled: (to, from, failure) => afterEach.forEach((fn) => fn(to, from, failure)),
	}
}

test("leaving a page dismisses every presented sheet before the navigation lands", async () => {
	const dismissed = []
	let open = ["day-sheet", "picker"]
	const { router, navigate } = fakeRouter()
	closeSheetsOnLeave(router, {
		getTop: async () =>
			open.at(-1) && { name: open.at(-1), dismiss: async () => dismissed.push(open.pop()) },
	})
	await navigate()
	assert.deepEqual(dismissed, ["picker", "day-sheet"])
})

test("no sheet open: the navigation is untouched", async () => {
	const { router, navigate } = fakeRouter()
	let asked = 0
	closeSheetsOnLeave(router, { getTop: async () => (asked++, undefined) })
	await navigate()
	assert.equal(asked, 1)
})

test("a sheet that refuses to close cannot hang navigation", async () => {
	const { router, navigate } = fakeRouter()
	let calls = 0
	closeSheetsOnLeave(router, {
		getTop: async () => ({ dismiss: async () => (calls++, false) }),
	})
	await navigate()
	assert.ok(calls <= 5, "bounded attempts")
})

test("a same-path navigation (query change) keeps the sheet", async () => {
	const { router, navigate } = fakeRouter()
	let asked = 0
	closeSheetsOnLeave(router, { getTop: async () => (asked++, undefined) })
	await navigate({ path: "/support" }, { path: "/support" })
	assert.equal(asked, 0)
})

// Android Back with a sheet open: the sheet closes and the page stays. A sheet
// has no history entry of its own, so Back used to close it AND leave the page.
// The guard cannot cancel the popstate (Ionic would animate the NEXT navigation
// as a back); it redirects to the page being left, which vue-router lands as a
// push and puts the browser stack back where it was. See sheetGuard.js.
function sheetStack(names) {
	const open = [...names]
	const dismissed = []
	return {
		dismissed,
		overlays: {
			getTop: async () =>
				open.length && { dismiss: async () => (dismissed.push(open.pop()), true) },
		},
	}
}

test("Back with a sheet open closes the sheet and stays on the page", async () => {
	const { router, pop } = fakeRouter()
	const { overlays, dismissed } = sheetStack(["day-sheet"])
	closeSheetsOnLeave(router, overlays)
	const result = await pop(-1)
	assert.deepEqual(dismissed, ["day-sheet"])
	assert.equal(result, "/more", "redirects to the page Back was leaving")
})

test("Back with a stack of sheets closes them all, then stays", async () => {
	const { router, pop } = fakeRouter()
	const { overlays, dismissed } = sheetStack(["day-sheet", "picker"])
	closeSheetsOnLeave(router, overlays)
	assert.equal(
		await pop(-1, { path: "/home", fullPath: "/home" }, { path: "/more", fullPath: "/more" }),
		"/more"
	)
	assert.deepEqual(dismissed, ["picker", "day-sheet"])
})

test("Back from a page with a query string stays on that exact URL", async () => {
	const { router, pop } = fakeRouter()
	const { overlays } = sheetStack(["day-sheet"])
	closeSheetsOnLeave(router, overlays)
	assert.equal(
		await pop(
			-1,
			{ path: "/home", fullPath: "/home" },
			{ path: "/dashboard/attendance", fullPath: "/dashboard/attendance?x=1" }
		),
		"/dashboard/attendance?x=1"
	)
})

test("Back with no sheet open goes back as before", async () => {
	const { router, pop } = fakeRouter()
	closeSheetsOnLeave(router, sheetStack([]).overlays)
	assert.equal(await pop(-1), undefined)
})

test("Back that a sheet refuses to close still goes back, never hangs", async () => {
	const { router, pop } = fakeRouter()
	closeSheetsOnLeave(router, { getTop: async () => ({ dismiss: async () => false }) })
	assert.equal(await pop(-1), undefined)
})

test("a jump of several pages back keeps today's behaviour: the stack cannot be restored", async () => {
	const { router, pop } = fakeRouter()
	const { overlays, dismissed } = sheetStack(["day-sheet"])
	closeSheetsOnLeave(router, overlays)
	assert.equal(await pop(-2), undefined)
	assert.deepEqual(dismissed, ["day-sheet"])
})

test("Forward with a sheet open closes the sheet and goes forward as before", async () => {
	const { router, pop } = fakeRouter()
	const { overlays, dismissed } = sheetStack(["day-sheet"])
	closeSheetsOnLeave(router, overlays)
	assert.equal(await pop(1), undefined)
	assert.deepEqual(dismissed, ["day-sheet"])
})

test("a tab switch or push with a sheet open still goes where it was asked", async () => {
	const { router, navigate } = fakeRouter()
	const { overlays, dismissed } = sheetStack(["day-sheet"])
	closeSheetsOnLeave(router, overlays)
	assert.equal(
		await navigate({ path: "/home", fullPath: "/home" }, { path: "/more", fullPath: "/more" }),
		undefined
	)
	assert.deepEqual(dismissed, ["day-sheet"])
})

test("a Back that ended without reaching the guard cannot turn a later push to the same page into a stay", async () => {
	const { router, listen, navigate, settled } = fakeRouter()
	const { overlays, dismissed } = sheetStack(["day-sheet"])
	closeSheetsOnLeave(router, overlays)
	// vue-router heard the popstate, an earlier guard aborted it: only the
	// listener and afterEach saw the Back
	listen("/home", "/more", -1)
	settled({ fullPath: "/home" }, { fullPath: "/more" }, { type: 4 })
	const to = { path: "/home", fullPath: "/home" }
	assert.equal(await navigate(to, { path: "/more", fullPath: "/more" }), undefined)
	assert.deepEqual(dismissed, ["day-sheet"])
})

test("a push to somewhere else while a Back is pending is not mistaken for that Back", async () => {
	const { router, listen, navigate } = fakeRouter()
	const { overlays } = sheetStack(["day-sheet"])
	closeSheetsOnLeave(router, overlays)
	listen("/home", "/more", -1)
	const to = { path: "/support", fullPath: "/support" }
	assert.equal(await navigate(to, { path: "/more", fullPath: "/more" }), undefined)
})

test("the redirect back onto the page keeps the next sheet: it is a same-page navigation", async () => {
	const { router, navigate } = fakeRouter()
	const { overlays, dismissed } = sheetStack(["day-sheet"])
	closeSheetsOnLeave(router, overlays)
	const here = { path: "/more", fullPath: "/more" }
	assert.equal(await navigate(here, here), undefined)
	assert.deepEqual(dismissed, [])
})

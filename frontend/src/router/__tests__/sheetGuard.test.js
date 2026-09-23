// A sheet must never outlive the page that opened it. Ionic presents an
// inline ion-modal at the app root, so a Back or a tab switch left the sheet
// floating over the next page, its scrim stranded in the hidden page, and the
// tab bar untappable (audit P0-3, reproduced live 23 Sep).
import { test } from "node:test"
import assert from "node:assert/strict"

import { closeSheetsOnLeave } from "../sheetGuard.js"

function fakeRouter() {
	const guards = []
	return {
		router: { beforeEach: (fn) => guards.push(fn) },
		navigate: async (to = { path: "/home" }, from = { path: "/dashboard/attendance" }) => {
			for (const guard of guards) await guard(to, from)
		},
	}
}

test("leaving a page dismisses every presented sheet before the navigation lands", async () => {
	const dismissed = []
	let open = ["day-sheet", "picker"]
	const { router, navigate } = fakeRouter()
	closeSheetsOnLeave(router, {
		getTop: async () => open.at(-1) && { name: open.at(-1), dismiss: async () => dismissed.push(open.pop()) },
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

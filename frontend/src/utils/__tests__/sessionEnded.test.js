// R1 (alpha.37): "the session ended" has ONE owner, sessionEnded() in personalCache.js. It marks the
// page as signed out (unless the person is logging out), starts clearing the offline copy of the
// /hrms page, hides the old account's rows and reloads onto Login: once per page, however many
// callers (user read, employee read, navigation guard, cookie watcher) notice at the same moment.
import { test, beforeEach } from "node:test"
import assert from "node:assert/strict"

let reloads = 0
let pageCopyCleared = 0
const store = new Map()
const style = {}
globalThis.window = { location: { origin: "https://nadi.test", reload: () => reloads++ }, addEventListener() {} }
globalThis.document = { cookie: "user_id=a%40x", addEventListener() {}, documentElement: { style } }
globalThis.localStorage = { getItem: () => null, setItem() {} }
globalThis.sessionStorage = {
	getItem: (k) => (store.has(k) ? store.get(k) : null),
	setItem: (k, v) => store.set(k, String(v)),
	removeItem: (k) => store.delete(k),
}
globalThis.indexedDB = undefined
globalThis.caches = {
	delete: async (name) => {
		assert.equal(name, "nadi-pages")
		pageCopyCleared++
		return true
	},
}

const fresh = async () => import(`../personalCache.js?${Math.random()}`)

beforeEach(() => {
	store.clear()
	reloads = 0
	pageCopyCleared = 0
	style.visibility = undefined
	document.cookie = "user_id=a%40x"
})

test("the session ended: signed-out mark, page copy cleared, page hidden, one reload", async () => {
	const { sessionEnded, takeSignedOutNotice } = await fresh()
	sessionEnded()
	assert.equal(reloads, 1)
	assert.equal(pageCopyCleared, 1)
	assert.equal(style.visibility, "hidden")
	assert.equal(takeSignedOutNotice(), true)
})

test("four callers noticing at once still reload once", async () => {
	const { sessionEnded } = await fresh()
	sessionEnded()
	sessionEnded()
	sessionEnded()
	sessionEnded()
	assert.equal(reloads, 1)
	assert.equal(pageCopyCleared, 1)
})

test("during a deliberate Log out: no mark, the page still goes", async () => {
	const { sessionEnded, markLoggingOut, takeSignedOutNotice } = await fresh()
	markLoggingOut()
	sessionEnded()
	assert.equal(reloads, 1)
	assert.equal(takeSignedOutNotice(), false)
})

test("a page that never had a user has no session to end: nothing happens", async () => {
	document.cookie = "user_id=Guest"
	const { sessionEnded, takeSignedOutNotice } = await fresh()
	sessionEnded()
	assert.equal(reloads, 0)
	assert.equal(pageCopyCleared, 0)
	assert.equal(takeSignedOutNotice(), false)
})

test("the cookie watcher goes through it: a cookie that turned Guest clears the page copy too", async () => {
	const { sessionIsCurrent, takeSignedOutNotice } = await fresh()
	document.cookie = "user_id=Guest"
	assert.equal(sessionIsCurrent(), false)
	assert.equal(sessionIsCurrent(), false, "and again: still one reload")
	assert.equal(reloads, 1)
	assert.equal(pageCopyCleared, 1)
	assert.equal(takeSignedOutNotice(), true)
})

test("another person signing in is not 'signed out': reload, no mark", async () => {
	const { sessionIsCurrent, takeSignedOutNotice } = await fresh()
	document.cookie = "user_id=b%40x"
	assert.equal(sessionIsCurrent(), false)
	assert.equal(reloads, 1)
	assert.equal(takeSignedOutNotice(), false)
})

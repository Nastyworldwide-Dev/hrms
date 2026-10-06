// AU-2: a session that ends mid-use (expired, signed out elsewhere) reloads
// the page onto Login, so a message shown on the old page is never seen. The
// mark is left for the Login page instead; a deliberate Log out leaves none.
import { test, beforeEach } from "node:test"
import assert from "node:assert/strict"

let reloads = 0
const store = new Map()
globalThis.window = { location: { origin: "https://nadi.test", reload: () => reloads++ }, addEventListener() {} }
globalThis.document = { cookie: "user_id=a%40x", addEventListener() {}, documentElement: { style: {} } }
globalThis.localStorage = { getItem: () => null, setItem() {} }
globalThis.sessionStorage = {
	getItem: (k) => (store.has(k) ? store.get(k) : null),
	setItem: (k, v) => store.set(k, String(v)),
	removeItem: (k) => store.delete(k),
}
globalThis.indexedDB = undefined

const fresh = async () => import(`../personalCache.js?${Math.random()}`)

beforeEach(() => {
	store.clear()
	reloads = 0
	document.cookie = "user_id=a%40x"
})

test("a session that ends on its own leaves one 'signed out' mark for Login", async () => {
	const { sessionIsCurrent, takeSignedOutNotice } = await fresh()
	document.cookie = "user_id=Guest"
	assert.equal(sessionIsCurrent(), false)
	assert.equal(reloads, 1)
	assert.equal(takeSignedOutNotice(), true)
	assert.equal(takeSignedOutNotice(), false, "shown once, then gone")
})

test("a deliberate Log out leaves no mark", async () => {
	const { sessionIsCurrent, markLoggingOut, takeSignedOutNotice } = await fresh()
	markLoggingOut()
	document.cookie = "user_id=Guest"
	sessionIsCurrent()
	assert.equal(takeSignedOutNotice(), false)
})

test("a page that never had a user leaves no mark", async () => {
	document.cookie = "user_id=Guest"
	const { sessionIsCurrent, takeSignedOutNotice } = await fresh()
	assert.equal(sessionIsCurrent(), true)
	assert.equal(takeSignedOutNotice(), false)
})

test("another person signing in on this phone is not 'signed out'", async () => {
	const { sessionIsCurrent, takeSignedOutNotice } = await fresh()
	document.cookie = "user_id=b%40x"
	sessionIsCurrent()
	assert.equal(takeSignedOutNotice(), false)
})

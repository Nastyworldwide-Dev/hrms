// iOS gate (scroll-and-shift), 25 + 27 Oct 2026: Approvals' loading placeholder is sized for one
// group (144 pt); an approver with 3 requests got a 292 pt group plus a Select-all row, so the
// answered panel under it jumped 208 pt on EVERY visit (frappe-ui reads its cache back after the
// first paint, so the cache never prevents it). Home's Needs you jumped 54 pt the same way. The
// last answered height is remembered per person and held while the next answer loads.
import { test, beforeEach } from "node:test"
import assert from "node:assert/strict"

import { rememberHeight, rememberedHeight } from "../placeholderHeight.js"

let store
beforeEach(() => {
	store = new Map()
	globalThis.localStorage = {
		getItem: (k) => (store.has(k) ? store.get(k) : null),
		setItem: (k, v) => store.set(k, String(v)),
		removeItem: (k) => store.delete(k),
	}
})

test("the last answered height comes back for the same person and block", () => {
	rememberHeight("approvals", "a@x", 292)
	assert.equal(rememberedHeight("approvals", "a@x"), 292)
	assert.equal(rememberedHeight("approvals", "b@x"), 0, "never another person's")
	assert.equal(rememberedHeight("needs-you", "a@x"), 0, "never another block's")
})

test("nothing remembered, no user, or a bad value holds no space", () => {
	assert.equal(rememberedHeight("approvals", "a@x"), 0)
	rememberHeight("approvals", null, 300)
	assert.equal(rememberedHeight("approvals", null), 0)
	store.set("hrms:ph:approvals:a@x", "nope")
	assert.equal(rememberedHeight("approvals", "a@x"), 0)
})

test("a page with no storage (private mode) still renders", () => {
	globalThis.localStorage = {
		getItem() {
			throw new Error("blocked")
		},
		setItem() {
			throw new Error("blocked")
		},
	}
	assert.doesNotThrow(() => rememberHeight("approvals", "a@x", 100))
	assert.equal(rememberedHeight("approvals", "a@x"), 0)
})

// Review of bcfbeaa8e/d612c8d07: (1) a block whose answer is empty disappears, so nothing was
// measured and the old tall height stayed: the next load held it, then jumped UP. An empty
// answer forgets. (2) Logout must not leave a key with the person's email on a shared phone.
import { forgetHeight, forgetAllHeights } from "../placeholderHeight.js"

test("an emptied block forgets its height", () => {
	rememberHeight("needs-you", "a@x", 300)
	forgetHeight("needs-you", "a@x")
	assert.equal(rememberedHeight("needs-you", "a@x"), 0)
})

test("logout forgets every remembered height, and only those", () => {
	rememberHeight("needs-you", "a@x", 300)
	rememberHeight("approvals", "b@x", 200)
	store.set("hrms:install-prompt-dismissed", "1")
	globalThis.localStorage.key = (i) => [...store.keys()][i] ?? null
	globalThis.localStorage.removeItem = (k) => store.delete(k)
	Object.defineProperty(globalThis.localStorage, "length", { get: () => store.size, configurable: true })
	forgetAllHeights()
	assert.deepEqual([...store.keys()], ["hrms:install-prompt-dismissed"])
})

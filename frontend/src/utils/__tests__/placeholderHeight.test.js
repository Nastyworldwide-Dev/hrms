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

// The browser tab and the PWA install name were the last vendor strings a
// Translation record could not reach — index.html is static, so <title> and
// apple-mobile-web-app-title shipped "Nadi" to every tenant regardless of
// what the tenant had translated. Found in the 8.x frontend audit.
//
// Run with: node --test "frontend/**/*.test.js"
import { test } from "node:test"
import assert from "node:assert/strict"

import { applyProductName } from "../productName.js"

/** Minimal document stand-in — the meta tag is optional on purpose. */
function fakeDoc({ title = "Nadi", withMeta = true } = {}) {
	const meta = { content: null, setAttribute(_, v) { this.content = v } }
	return {
		title,
		_meta: meta,
		querySelector: (sel) =>
			withMeta && sel === 'meta[name="apple-mobile-web-app-title"]' ? meta : null,
	}
}

test("applies the translated name to both the title and the install name", () => {
	const doc = fakeDoc()
	const name = applyProductName((s) => (s === "Nadi" ? "NSTY People" : s), doc)

	assert.equal(name, "NSTY People")
	assert.equal(doc.title, "NSTY People", "browser tab")
	assert.equal(doc._meta.content, "NSTY People", "PWA install name")
})

test("leaves the document alone when nothing is translated", () => {
	// `__` returns the source string when no record exists — that must not be
	// mistaken for a translation, but it is also not a reason to blank the title.
	const doc = fakeDoc()
	applyProductName((s) => s, doc)
	assert.equal(doc.title, "Nadi")
})

test("falls back to the shipped title when there is no translate function", () => {
	const doc = fakeDoc({ title: "Something Else" })
	assert.equal(applyProductName(undefined, doc), "Something Else")
	assert.equal(doc.title, "Something Else")
})

test("does not throw when the meta tag is absent", () => {
	const doc = fakeDoc({ withMeta: false })
	assert.doesNotThrow(() => applyProductName((_s) => "NSTY People", doc))
	assert.equal(doc.title, "NSTY People")
})

// FilePreviewModal threw on every close of the request sheet (crash hunt,
// 28 Sep 2026): "TypeError: Failed to execute 'createObjectURL' on 'URL':
// Overload resolution failed", reported by the app's own diagnostics as a
// vue.render error in onBeforeUnmount. Its callers start with `file = {}`, and
// the unmount cleanup read `src`, which called URL.createObjectURL({}).
// A preview URL is made only for a real File/Blob, once, and revoked once.
import assert from "node:assert/strict"
import { test } from "node:test"

import { previewSource } from "../../utils/previewSource.js"

class FakeBlob {}

function url() {
	const made = []
	const revoked = []
	return {
		made,
		revoked,
		api: {
			createObjectURL: (b) => {
				if (!(b instanceof FakeBlob)) throw new TypeError("Overload resolution failed.")
				made.push(b)
				return `blob:${made.length}`
			},
			revokeObjectURL: (u) => revoked.push(u),
		},
	}
}

test("an empty placeholder file makes no URL and never throws", () => {
	const u = url()
	const s = previewSource({}, u.api, FakeBlob)
	assert.equal(s.src, "")
	s.release()
	assert.deepEqual(u.made, [])
	assert.deepEqual(u.revoked, [])
})

test("no file at all is the same", () => {
	const u = url()
	const s = previewSource(null, u.api, FakeBlob)
	assert.equal(s.src, "")
	s.release()
})

test("a saved attachment uses its own URL and makes none", () => {
	const u = url()
	const s = previewSource({ file_url: "/files/a.png" }, u.api, FakeBlob)
	assert.equal(s.src, "/files/a.png")
	s.release()
	assert.deepEqual(u.made, [])
})

test("a picked file gets one URL, released once", () => {
	const u = url()
	const blob = new FakeBlob()
	const s = previewSource(blob, u.api, FakeBlob)
	assert.equal(s.src, "blob:1")
	s.release()
	s.release()
	assert.deepEqual(u.revoked, ["blob:1"])
})

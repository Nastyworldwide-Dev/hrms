// The toast wrapper is the app's one voice (spec §11.3, revamp slice A7).
//
// gToast wraps frappe-ui's toast rather than replacing it: the queue, the
// teleport and the auto-dismiss are sound, and only the skin and the copy
// rules were ours. Slice A7 added a third thing it owns — the ANNOUNCEMENT —
// because the vendor toast has no role and no aria-live, and a toast takes no
// focus, so nothing it said ever reached a screen reader.
//
// Behaviour through the module's own surface, not its text: these assertions
// are about which variant maps to which severity and what the wrapper hands
// the announcer, both of which a rewrite could silently get wrong.
//
// It lives in tests/ rather than beside the module because it needs
// mock.module, which bun has not implemented — and the pre-commit hook runs
// mapped tests under bun. tests/*.mjs is where this repo's other
// mock.module tests already live, for the same reason.
// Run: cd frontend && node --experimental-test-module-mocks --test tests/toast-announces.test.mjs
import { test, beforeEach, mock } from "node:test"
import assert from "node:assert/strict"

//: frappe-ui cannot be imported under plain node — its index re-exports through
//: directory specifiers, which ESM does not resolve — so the ONE function this
//: module uses from it is mocked, the same way tests/approved-cancel.test.mjs
//: mocks createResource. The calls are captured so a test can assert that the
//: visible toast still happens alongside the announcement.
const shown = []
mock.module("frappe-ui", {
	namedExports: {
		toast(options) {
			shown.push(options)
			return options
		},
	},
})

//: frappe-ui's toast reaches for the DOM at import time in some versions, and
//: the announcer needs a document to attach its region to. Both are stubbed so
//: this runs without jsdom.
function fakeDom() {
	const created = []
	globalThis.document = {
		createElement() {
			const el = {
				attrs: {},
				style: {},
				textContent: "",
				setAttribute(k, v) {
					this.attrs[k] = v
				},
				getAttribute(k) {
					return this.attrs[k]
				},
				remove() {},
			}
			created.push(el)
			return el
		},
		body: { appendChild() {} },
		getElementById: () => null,
	}
	return created
}

let created
beforeEach(async () => {
	created = fakeDom()
	const { __resetAnnouncer } = await import(
		"../src/components/glass/announce.js"
	)
	__resetAnnouncer()
	shown.length = 0
})

test("an error interrupts, and says both lines", async () => {
	const { gToast } = await import("../src/components/glass/toast.js")
	gToast({
		title: "Could not check you in",
		text: "Move somewhere with signal",
		variant: "error",
	})
	await Promise.resolve()
	const region = created.find(
		(el) => el.getAttribute("aria-live") === "assertive"
	)
	assert.ok(region, "an error announces assertively")
	// Both lines, joined into one sentence: the title says what happened and
	// the text says what to do, and hearing only the first is being told a
	// problem with no way out.
	assert.equal(
		region.textContent,
		"Could not check you in. Move somewhere with signal"
	)
})

test("a success waits its turn", async () => {
	const { gToast } = await import("../src/components/glass/toast.js")
	gToast({ title: "Leave request submitted", variant: "success" })
	await Promise.resolve()
	const region = created.find((el) => el.getAttribute("aria-live") === "polite")
	assert.ok(region, "success is polite")
	assert.equal(region.textContent, "Leave request submitted")
	assert.ok(
		!created.some((el) => el.getAttribute("aria-live") === "assertive"),
		"a save must not interrupt whatever is being read"
	)
	// The announcement is IN ADDITION to the toast, never instead of it.
	assert.equal(shown.length, 1, "a sighted user still sees it")
	assert.equal(shown[0].type, "success", "and it keeps the variant's styling")
})

test("a toast with no text announces just the title", async () => {
	// The join must not leave a trailing separator, which a reader speaks.
	const { gToast } = await import("../src/components/glass/toast.js")
	gToast({ title: "Saved" })
	await Promise.resolve()
	const region = created.find((el) => el.getAttribute("aria-live") === "polite")
	assert.equal(region.textContent, "Saved")
})

test("an unknown variant falls back to info rather than throwing", async () => {
	// Call sites pass a string; a typo must degrade to a spoken, visible toast
	// rather than an exception on the screen that was reporting a problem.
	const { gToast } = await import("../src/components/glass/toast.js")
	gToast({ title: "Something happened", variant: "nonsense" })
	await Promise.resolve()
	const region = created.find((el) => el.getAttribute("aria-live") === "polite")
	assert.equal(region.textContent, "Something happened")
})

// alpha.7 Phase 4: two requests failing together stacked two identical
// "Something didn't load" banners. iOS shows one; the same message again
// within a few seconds is the same news.
test("the same message twice in a row shows once", async () => {
	const { gToast, __resetRecent } = await import("../src/components/glass/toast.js")
	__resetRecent()
	shown.length = 0
	gToast({ title: "Something didn't load", text: "Try again", variant: "error" })
	gToast({ title: "Something didn't load", text: "Try again", variant: "error" })
	gToast({ title: "Saved", variant: "success" })
	assert.deepEqual(
		shown.map((s) => s.title),
		["Something didn't load", "Saved"]
	)
})

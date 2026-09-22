// Every confirmation and every failure was silent to a screen reader
// (revamp slice A7, WCAG 2.2 SC 4.1.3 Status Messages).
//
// A toast appears without taking focus, so assistive technology has no reason
// to look at it: it must be inside a live region or it is never spoken. This
// app delivers every "Leave request submitted" and every "Could not check you
// in" through frappe-ui's toast, and Toast.vue carries no role and no
// aria-live — verified against the installed package, not assumed. Sixteen
// call sites, silent.
//
// The region is OURS rather than a patch to the vendor component, because the
// toast root is created imperatively and teleported into, so attributes added
// to it would need patch-package and would be lost on every upgrade.
import { test, beforeEach } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")

//: The smallest DOM this module touches. jsdom is not a dependency here, and
//: what is being tested is the module's own behaviour — which element it
//: creates, what it puts on it, and when it rewrites the text.
function fakeDom() {
	const created = []
	const body = {
		children: [],
		appendChild(el) {
			this.children.push(el)
		},
	}
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
		body,
	}
	return { created, body }
}

let dom
beforeEach(async () => {
	dom = fakeDom()
	const { __resetAnnouncer } = await import("../announce.js")
	__resetAnnouncer()
})

test("a polite announcement lands in a live region that already existed", async () => {
	const { announce } = await import("../announce.js")
	announce("Leave request submitted")
	const [el] = dom.created
	assert.ok(el, "a region was created")
	assert.equal(el.getAttribute("aria-live"), "polite")
	assert.equal(el.getAttribute("role"), "status")
	// A whole sentence, not a diff. Without atomic, a reader may speak only the
	// words that CHANGED between two messages — "Leave approved" then "Leave
	// rejected" becomes the single word "rejected".
	assert.equal(el.getAttribute("aria-atomic"), "true")
	await Promise.resolve()
	assert.equal(el.textContent, "Leave request submitted")
})

test("an error interrupts; a success waits its turn", async () => {
	const { announce } = await import("../announce.js")
	announce("Could not check you in", "assertive")
	const [el] = dom.created
	assert.equal(el.getAttribute("aria-live"), "assertive")
	assert.equal(el.getAttribute("role"), "alert")
})

test("the same message twice is spoken twice", async () => {
	// Setting an identical string produces no mutation, so a SECOND failed save
	// would be silent — precisely the moment somebody needs telling again. The
	// region is cleared first to force the change.
	const { announce } = await import("../announce.js")
	announce("Could not save")
	await Promise.resolve()
	const [el] = dom.created
	assert.equal(el.textContent, "Could not save")
	announce("Could not save")
	assert.equal(el.textContent, "", "cleared, so the next write is a real mutation")
	await Promise.resolve()
	assert.equal(el.textContent, "Could not save")
})

test("the region is invisible, but not display:none", async () => {
	// display:none is not announced by anything. The clip-path technique keeps
	// the node rendered and off-screen.
	const { announce } = await import("../announce.js")
	announce("x")
	const [el] = dom.created
	assert.equal(el.style.display, undefined, "never display:none")
	assert.equal(el.style.clipPath, "inset(50%)")
	assert.equal(el.style.width, "1px")
})

test("one region is reused, not one per message", async () => {
	// A live region must exist BEFORE the text lands in it; assistive tech
	// watches existing nodes for mutations rather than re-scanning the page,
	// so a region created and filled in the same tick is frequently missed.
	const { announce } = await import("../announce.js")
	announce("one")
	announce("two")
	announce("three")
	assert.equal(dom.created.length, 1, "three messages, one region")
})

test("every toast announces, because the vendor toast does not", () => {
	// The dependency's own markup, read rather than assumed. If a future
	// frappe-ui adds aria-live, this test tells us the wrapper is now belt and
	// braces rather than the only thing speaking.
	const vendor = read("../node_modules/frappe-ui/src/components/Toast.vue")
	assert.doesNotMatch(vendor, /aria-live|role="(status|alert)"/, "vendor toast is still silent")
	const wrapper = read("components/glass/toast.js")
	assert.match(wrapper, /import \{ announce \}/, "the wrapper speaks for it")
	assert.match(
		wrapper,
		/variant === "error" \? "assertive" : "polite"/,
		"an error interrupts, a success does not"
	)
})

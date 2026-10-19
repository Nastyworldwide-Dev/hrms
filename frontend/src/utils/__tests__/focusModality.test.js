// The lime focus ring showed after a tap (owner, 19 Oct 2026: "this type of
// outline ... it happen to be everywhere"). Browsers draw :focus-visible after
// ANY key (Escape closing a sheet) and when code moves focus (a sheet focusing
// itself on open, focus returned to the row that opened it). The app records
// how the person is moving through it; the ring is for keyboard movement only.
import { test } from "node:test"
import assert from "node:assert/strict"
import { focusModality } from "../focusModality.js"

function fakeDocument() {
	const listeners = {}
	return {
		documentElement: { dataset: {} },
		addEventListener: (type, fn) => (listeners[type] = fn),
		fire: (type, event = {}) => listeners[type]?.(event),
	}
}

test("a tap or click is pointer movement", () => {
	const doc = fakeDocument()
	focusModality(doc)
	doc.fire("pointerdown")
	assert.equal(doc.documentElement.dataset.input, "pointer")
})

test("Tab and the arrow keys are keyboard movement", () => {
	for (const key of ["Tab", "ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight"]) {
		const doc = fakeDocument()
		focusModality(doc)
		doc.fire("pointerdown")
		doc.fire("keydown", { key })
		assert.equal(doc.documentElement.dataset.input, "keyboard", key)
	}
})

test("Escape or typing after a tap does not turn the ring on", () => {
	const doc = fakeDocument()
	focusModality(doc)
	doc.fire("pointerdown")
	for (const key of ["Escape", "a", "Enter", "Shift"]) doc.fire("keydown", { key })
	assert.equal(doc.documentElement.dataset.input, "pointer")
})

test("before any input the app assumes a tap, the common case on a phone", () => {
	const doc = fakeDocument()
	focusModality(doc)
	assert.equal(doc.documentElement.dataset.input, "pointer")
})

test("one CSS rule hides every ring while the person is tapping, and main.js arms it", async () => {
	const { readFileSync } = await import("node:fs")
	const read = (p) => readFileSync(new URL(p, import.meta.url), "utf8")
	const css = read("../../theme/glass-components.css")
	const rule =
		css.match(/html\[data-input="pointer"\] :focus-visible,[\s\S]*?\{[^}]*\}/)?.[0] || ""
	assert.match(rule, /box-shadow: none !important/)
	// rings drawn on a parent (switch track, time-slip file row) are covered too
	assert.match(rule, /\.g-switch--drawn:has\(:focus-visible\) \.g-switch__track/)
	assert.match(rule, /\.timeslip-file:has\(input:focus-visible\)/)
	assert.match(read("../../main.js"), /\nfocusModality\(\)\n/)
})

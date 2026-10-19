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

test("Enter, Space or a letter on a control is keyboard use (WCAG 2.4.7)", () => {
	// Tap once, then Enter on a focused button: the person is on the keyboard
	// and must see where focus went (design review of the focus commit).
	for (const key of ["Enter", " ", "a"]) {
		const doc = fakeDocument()
		focusModality(doc)
		doc.fire("pointerdown")
		doc.fire("keydown", { key, target: { tagName: "BUTTON" } })
		assert.equal(doc.documentElement.dataset.input, "keyboard", JSON.stringify(key))
	}
})

test("Escape, a bare modifier, or typing in a field after a tap keeps the ring off", () => {
	// Escape closing a sheet was the owner's complaint; typing in a text
	// field is writing, not moving.
	const doc = fakeDocument()
	focusModality(doc)
	doc.fire("pointerdown")
	for (const key of ["Escape", "Shift", "Control", "Alt", "Meta"])
		doc.fire("keydown", { key, target: { tagName: "BUTTON" } })
	for (const key of ["a", " ", "Enter"])
		doc.fire("keydown", { key, target: { tagName: "TEXTAREA" } })
	doc.fire("keydown", { key: "b", target: { tagName: "DIV", isContentEditable: true } })
	assert.equal(doc.documentElement.dataset.input, "pointer")
})

test("before any input the ring shows as normal", () => {
	// Nothing is hidden until a tap says the person is using a pointer.
	const doc = fakeDocument()
	focusModality(doc)
	assert.equal(doc.documentElement.dataset.input, undefined)
})

test("one CSS rule hides every ring while the person is tapping, and main.js arms it", async () => {
	const { readFileSync } = await import("node:fs")
	const read = (p) => readFileSync(new URL(p, import.meta.url), "utf8")
	const css = read("../../theme/glass-components.css")
	const rule =
		css.match(/html\[data-input="pointer"\] :focus-visible[\s\S]*?\{[^}]*\}/)?.[0] || ""
	assert.match(rule, /box-shadow: none !important/)
	// a text field keeps its own focus cue while someone types in it
	assert.match(rule, /:focus-visible:not\(input, textarea, select, \[contenteditable\]\)/)
	// rings drawn on a parent (switch track, time-slip file row) are covered too
	assert.match(rule, /\.g-switch--drawn:has\(:focus-visible\) \.g-switch__track/)
	assert.match(rule, /\.timeslip-file:has\(input:focus-visible\)/)
	assert.match(read("../../main.js"), /\nfocusModality\(\)\n/)
})

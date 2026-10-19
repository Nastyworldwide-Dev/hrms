// The lime focus ring is for people moving with a keyboard (owner, 19 Oct
// 2026: the ring showed "everywhere" after a tap). Browsers draw :focus-visible
// after ANY key press (Escape closing a sheet) and whenever code moves focus (a
// sheet focusing itself on open, focus returned to the row that opened it), so
// after a tap the ring landed on rows nobody had keyed to. This records how the
// person is moving: <html data-input="pointer|keyboard">; the CSS keeps every
// ring and hides it only while data-input is "pointer". Until the first tap
// nothing is hidden (WCAG 2.4.7).
//
// Keyboard use is any key on a control except Escape and bare modifiers:
// Enter or Space on a button moves focus too. Typing inside a text field is
// writing, not moving, so it does not switch.
const NOT_MOVING = new Set(["Escape", "Shift", "Control", "Alt", "Meta", "CapsLock"])
const isTextEntry = (el) =>
	!!el && (el.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName))

export function focusModality(doc = globalThis.document) {
	if (!doc?.addEventListener) return
	const set = (mode) => {
		if (doc.documentElement.dataset.input !== mode) doc.documentElement.dataset.input = mode
	}
	doc.addEventListener("pointerdown", () => set("pointer"), true)
	doc.addEventListener(
		"keydown",
		(event) => {
			if (event.key === "Tab" || (!NOT_MOVING.has(event.key) && !isTextEntry(event.target)))
				set("keyboard")
		},
		true
	)
	console.info("[focusModality] focus ring follows keyboard movement only")
}

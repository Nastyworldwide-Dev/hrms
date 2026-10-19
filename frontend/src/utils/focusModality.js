// The lime focus ring is for people moving with a keyboard (owner, 19 Oct
// 2026: the ring showed "everywhere" after a tap). Browsers draw :focus-visible
// after ANY key press (Escape closing a sheet) and whenever code moves focus (a
// sheet focusing itself on open, focus returned to the row that opened it), so
// after a tap the ring landed on rows nobody had keyed to. This records how the
// person is moving: <html data-input="pointer|keyboard">; the CSS keeps every
// ring and hides it while data-input is "pointer".
const NAVIGATION_KEYS = new Set([
	"Tab",
	"ArrowDown",
	"ArrowUp",
	"ArrowLeft",
	"ArrowRight",
	"Home",
	"End",
	"PageUp",
	"PageDown",
])

export function focusModality(doc = globalThis.document) {
	if (!doc?.addEventListener) return
	const set = (mode) => {
		if (doc.documentElement.dataset.input !== mode) doc.documentElement.dataset.input = mode
	}
	set("pointer")
	doc.addEventListener("pointerdown", () => set("pointer"), true)
	doc.addEventListener(
		"keydown",
		(event) => {
			if (NAVIGATION_KEYS.has(event.key)) set("keyboard")
		},
		true
	)
	console.info("[focusModality] focus ring follows keyboard movement only")
}

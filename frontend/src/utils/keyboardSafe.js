// The field you type in, and the Send bar under it, stay above the keyboard
// (alpha.12 K23). Apple (virtual-keyboards): "keep important parts of your
// interface visible while the virtual keyboard is onscreen".
//
// Android Chrome/Firefox honour `interactive-widget=resizes-content` in the
// viewport meta (index.html) and shrink the page themselves. iOS Safari does
// not yet (WebKit landed it Aug 2026, no Safari release), so the keyboard
// overlays the page there: this reads the visual viewport, exposes the
// covered height as --g-keyboard-inset (the sticky Send bar lifts by it), and
// scrolls the focused field into the part that is still visible.

//: How much of the layout viewport the keyboard covers, in px. Pure.
export function keyboardInset(layoutHeight, visualHeight, visualTop = 0) {
	const covered = Math.round(layoutHeight - visualHeight - visualTop)
	return covered > 80 ? covered : 0 // < 80 px is browser chrome moving, not a keyboard
}

export function keyboardSafe(win = globalThis.window) {
	const vv = win?.visualViewport
	if (!vv || !win.document) return null
	const root = win.document.documentElement
	let last = -1
	const update = () => {
		const inset = keyboardInset(win.innerHeight, vv.height, vv.offsetTop)
		if (inset === last) return
		last = inset
		root.style.setProperty("--g-keyboard-inset", `${inset}px`)
		if (!inset) return
		const field = win.document.activeElement
		if (field?.matches?.("input, textarea, select, [contenteditable=true]")) {
			field.scrollIntoView({ block: "center", behavior: "smooth" })
		}
	}
	vv.addEventListener("resize", update)
	vv.addEventListener("scroll", update)
	console.info("[keyboardSafe] fields stay above the keyboard")
	return update
}

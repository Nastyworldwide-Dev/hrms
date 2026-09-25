// Zoom is off (owner ruling, 25 Sep 2026: "turn off zoom"). iOS Safari has
// ignored user-scalable=no since iOS 10, so the pinch is stopped at its own
// gesture events and at a two-finger touchmove; double-tap zoom is already off
// through `touch-action: manipulation` (glass-components.css). The phone's own
// Text Size setting still applies, so reading help is not taken away.
export function blockZoom(target = globalThis.document) {
	if (!target?.addEventListener) return
	const stop = (event) => event.preventDefault()
	for (const type of ["gesturestart", "gesturechange", "gestureend"]) {
		target.addEventListener(type, stop, { passive: false })
	}
	target.addEventListener(
		"touchmove",
		(event) => {
			if (event.touches && event.touches.length > 1) event.preventDefault()
		},
		{ passive: false }
	)
	console.info("[blockZoom] pinch zoom disabled")
}

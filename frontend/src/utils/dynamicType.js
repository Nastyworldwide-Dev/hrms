// The app follows the iPhone's Text Size (Settings > Display & Brightness), as a
// native screen does (Apple HIG Typography, Dynamic Type; alpha.56).
//
// glass-components.css gives html the system body font (-apple-system-body) on
// iPhone and iPad, and every size in the app is rem, so it all scales from the
// root. At the default setting that font is 17px, but the app is drawn on a 16px
// root, so the root is set to the system size x 16/17: the default looks exactly
// as before and a larger setting grows everything in proportion. CSS alone cannot
// do the scaling: an em on the root reads the browser default, not this font.
//
// Read once at start-up. A change of Text Size while the app is open applies on
// the next open, which is how Safari treats it too.
// ceiling: read at launch only; upgrade: re-read on visibilitychange if staff
// report having to reopen the app after changing Text Size.

const IOS_DEFAULT_BODY_PX = 17
const APP_ROOT_PX = 16

//: The root size for a system body size, or null when there is none to follow.
export function rootSizeFor(systemPx) {
	const px = Number(systemPx)
	if (!Number.isFinite(px) || px <= 0) return null
	return px * (APP_ROOT_PX / IOS_DEFAULT_BODY_PX)
}

//: Same condition as the CSS rule: the system body font exists and this is a touch
//: device (a Mac also has the font, at 13px).
const isIPhoneLike = (css) =>
	Boolean(
		css?.supports?.("font: -apple-system-body") &&
			css?.supports?.("-webkit-touch-callout: default")
	)

export function dynamicType(doc = globalThis.document, css = globalThis.CSS) {
	if (!doc?.documentElement || !isIPhoneLike(css)) return
	const systemPx = parseFloat(doc.defaultView?.getComputedStyle(doc.documentElement).fontSize)
	const root = rootSizeFor(systemPx)
	if (root === null) return
	doc.documentElement.style.fontSize = `${root}px`
	console.info("[dynamicType] text size follows the phone:", systemPx, "->", root)
}

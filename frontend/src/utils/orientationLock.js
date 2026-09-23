// Phones are portrait-locked; tablets and desktop adapt (owner ruling, 22 Sep
// 2026; audit F-3). A manifest `orientation` would lock the installed app on
// every device, tablets included, so the lock is requested here instead, and
// only where it applies. WCAG 1.3.4 allows the restriction on phones because
// the check-in camera and the sheets are built for one orientation there;
// larger screens stay free.

//: A phone's short side is under the tablet breakpoint (768px, Tailwind md).
const PHONE_MAX_SHORT_SIDE = 768

export function shouldLockPortrait({ shortSide, standalone, canLock }) {
	return Boolean(standalone && canLock && shortSide < PHONE_MAX_SHORT_SIDE)
}

export async function lockPortraitOnPhones(env = readEnvironment()) {
	if (!shouldLockPortrait(env)) return
	try {
		await env.orientation.lock("portrait")
		console.info("[orientation] locked to portrait on an installed phone")
	} catch (error) {
		// Refused (not fullscreen, or unsupported): the app still works rotated.
		console.warn("[orientation] portrait lock refused", error?.name || error)
	}
}

function readEnvironment() {
	const orientation = window.screen?.orientation
	return {
		shortSide: Math.min(window.screen?.width || 0, window.screen?.height || 0),
		standalone: window.matchMedia?.("(display-mode: standalone)").matches ?? false,
		canLock: typeof orientation?.lock === "function",
		orientation,
	}
}

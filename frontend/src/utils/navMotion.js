// Which page transition a navigation gets (audit F-4). One pure rule, so the
// Ionic animation builder in ionicConfig.js is only plumbing.
//
// Sources: Apple HIG (the push is iOS's own idiom; tab switches never
// animate), Material 3 motion (fade-through between destinations), NN/g
// "Executing UX Animations" (100–500 ms, shorter for frequent actions), and
// WCAG 2.3.3 (motion can be turned off).
const DESKTOP_MIN_WIDTH = 1024

export function pickNavMotion({ reducedMotion, width, ios, direction, gesture }) {
	if (reducedMotion) return { kind: "none" }
	// The browser or OS already animated an edge-swipe back; a second slide
	// on top is the "double animation" people saw.
	if (direction === "back" && gesture) return { kind: "none" }
	if (width >= DESKTOP_MIN_WIDTH) return { kind: "fade", duration: 150 }
	if (ios) return { kind: "ios" }
	return { kind: "fade", duration: 200 }
}

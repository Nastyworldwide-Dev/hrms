// Whether the navigation in progress came from the browser's own history (an
// edge swipe, the Android back button, the browser Back). The OS or browser
// has already animated those, so the page transition must not slide again
// (audit F-4). Set by router/traversalQueue.js, read by utils/ionicConfig.js.
let browserTraversal = false

export function markBrowserTraversal(value) {
	browserTraversal = value
}

export function isBrowserTraversal() {
	return browserTraversal
}

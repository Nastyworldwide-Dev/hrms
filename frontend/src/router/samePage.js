// A navigation that stays on the page it left: a query or hash change, or a Back that sheetGuard.js
// redirected onto the page being left. sheetGuard.js and focusRelease.js both ask this, so the two
// guards cannot disagree about what "the same page" is.
export function samePage(to, from) {
	return to.path === from.path
}

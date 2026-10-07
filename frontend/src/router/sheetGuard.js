// Close every open sheet before a navigation lands.
//
// Ionic presents an inline ion-modal at the app root, outside the page that
// opened it. Nothing closed it on Back, on a tab switch or on a pushed route,
// so the sheet floated over the next page, its scrim stayed behind in the
// hidden page, and the tab bar under it stopped taking taps (audit P0-3,
// reproduced live 23 Sep 2026).
//
// Back with a sheet open closes the sheet and stays on the page (Android
// expects it). A sheet owns no history entry, so by the time the guard runs the
// browser has already stepped back one page. The guard cannot cancel that
// popstate: vue-router would restore the stack, but @ionic/vue-router 7.4.3's
// afterEach returns on the failure without clearing the pop it recorded from
// history.listen, so the NEXT navigation animated as a back (see
// traversalQueue.js). Instead the guard REDIRECTS to the page being left. A
// guard redirect is not a failure Ionic sees; the redirect's own successful
// afterEach consumes the recorded pop, and the landing is a push onto the entry
// the Back vacated, so the stack has the length it had (e2e/sheet-back-stays.spec.js).
//
// ceiling: only a one-entry Back is handled. A jump of several entries
// (history.go(-2)) or a Forward cannot be put back with one push, so the sheet
// closes and the page goes where the browser sent it, as before. Any entries
// ahead of the page after a Back are dropped by the re-push, as for any push.
// upgrade: when @ionic/vue-router clears its pop info on a failed navigation,
// return false here for every Back instead, and drop the redirect.

//: A sheet whose dismiss is refused (canDismiss, a pending save) must not hang
//: every navigation after it.
const MAX_DISMISSALS = 5
const NAVIGATION_CANCELLED = 8 // vue-router ErrorTypes.NAVIGATION_CANCELLED

export function closeSheetsOnLeave(router, overlays) {
	// Where the one-entry Back that vue-router is navigating for is going, until a
	// navigation settles. Heard on RouterHistory.listen, which fires only for a
	// popstate (traversalQueue.js reads it the same way).
	let backTo = null
	router.options.history.listen((to, _from, info) => {
		backTo = info.type === "pop" && info.delta === -1 ? router.resolve(to).fullPath : null
	})
	router.afterEach((to, _from, failure) => {
		// A cancelled failure for another location is an older navigation the Back
		// itself cancelled: the Back is still running.
		if (!failure || failure.type !== NAVIGATION_CANCELLED || to.fullPath === backTo) backTo = null
	})

	router.beforeEach(async (to, from) => {
		const isBack = backTo !== null && to.fullPath === backTo
		if (isBack) backTo = null
		if (to.path === from.path) return
		let closed = false
		for (let i = 0; i < MAX_DISMISSALS; i++) {
			const top = await overlays.getTop()
			if (!top) {
				// Every sheet is gone: a Back stays on the page it left.
				if (closed && isBack) return from.fullPath
				return
			}
			console.info("[sheetGuard] closing an open sheet before leaving", from.path, "->", to.path)
			if ((await top.dismiss()) === false) {
				console.warn("[sheetGuard] a sheet refused to close; navigating anyway")
				return
			}
			closed = true
		}
	})
}

// Close every open sheet before a navigation lands.
//
// Ionic presents an inline ion-modal at the app root, outside the page that
// opened it. Nothing closed it on Back, on a tab switch or on a pushed route,
// so the sheet floated over the next page, its scrim stayed behind in the
// hidden page, and the tab bar under it stopped taking taps (audit P0-3,
// reproduced live 23 Sep 2026).
//
// ceiling: Back with a sheet open closes the sheet AND goes back, where Android
// predictive back would close the sheet and stay. Cancelling a popstate leaves
// @ionic/vue-router's pending pop uncleared (see traversalQueue.js), so the next
// page would animate as a back. upgrade: when @ionic/vue-router clears its pop
// info on a failed navigation, return false here for a Back instead.

//: A sheet whose dismiss is refused (canDismiss, a pending save) must not hang
//: every navigation after it.
const MAX_DISMISSALS = 5

export function closeSheetsOnLeave(router, overlays) {
	router.beforeEach(async (to, from) => {
		if (to.path === from.path) return
		for (let i = 0; i < MAX_DISMISSALS; i++) {
			const top = await overlays.getTop()
			if (!top) return
			console.info("[sheetGuard] closing an open sheet before leaving", from.path, "->", to.path)
			const closed = await top.dismiss()
			if (closed === false) {
				console.warn("[sheetGuard] a sheet refused to close; navigating anyway")
				return
			}
		}
	})
}

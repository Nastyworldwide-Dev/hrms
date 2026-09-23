import { markBrowserTraversal } from "../utils/browserTraversal.js"
// Hold push/replace while a Back/Forward (a history traversal) is still in flight.
//
// Every navigation here waits on main.js's guard (a userResource.reload round
// trip), so a Back stays in flight for ~100-600 ms. A push or tap in that window
// CANCELS the Back. vue-router accepts the cancel and keeps the browser history
// where the Back put it — but @ionic/vue-router cannot follow: its afterEach
// returns on the failure without clearing the "pop" it recorded from
// history.listen, so the NEXT navigation is animated as a back. The previous
// page stays painted while the route and URL are the new page, which never
// renders until a reload (e2e/back-race.spec.js).
//
// The traversal is detected through vue-router's own RouterHistory.listen — it
// fires exactly when vue-router starts a navigation for a popstate, so a
// popstate vue-router ignores (a hash-only change) cannot hold the queue shut.
// It settles on its own afterEach (landed, aborted or cancelled by a newer
// traversal), on any successful landing (a guard redirect), on any failure other
// than a cancel (a guard redirect that was itself aborted), or on onError. Only a
// CANCELLED failure for another location keeps it shut: that one is the older
// navigation the traversal itself cancelled, so the traversal is still running.
//
// Nothing is held before the app's first navigation has landed: vue-router only
// starts following popstate then, so an earlier hold would never be released.
const NAVIGATION_CANCELLED = 8 // vue-router ErrorTypes.NAVIGATION_CANCELLED

export function queueBehindTraversal(router) {
	let ready = false
	let pending = null
	let release = null
	let target = null

	const settle = () => {
		release?.()
		pending = release = target = null
	}

	router.options.history.listen((to) => {
		// The browser drove this one (swipe, system back, Back button): it has
		// already animated it, so Ionic must not slide on top (audit F-4).
		markBrowserTraversal(true)
		if (!ready) return
		target = router.resolve(to).fullPath
		if (!pending) pending = new Promise((resolve) => (release = resolve))
	})

	router.afterEach((to, _from, failure) => {
		if (!failure) ready = true
		if (!pending) return
		if (!failure || failure.type !== NAVIGATION_CANCELLED || to.fullPath === target) settle()
	})
	router.onError(() => settle())

	for (const method of ["push", "replace"]) {
		const navigate = router[method].bind(router)
		router[method] = (to) => {
			// An in-app navigation: the page transition is ours to animate. (The
			// flag stays set for the whole browser Back, however late Ionic
			// starts its transition after the new page mounts.)
			markBrowserTraversal(false)
			if (!pending) return navigate(to)
			console.info(`[router] ${method} held until the Back/Forward to ${target} lands`)
			return pending.then(() => navigate(to))
		}
	}
	return router
}

// Release focus before every navigation. Ionic keeps the outgoing page mounted
// and stamps it aria-hidden — but the control that triggered the navigation
// still holds focus inside it, so the browser reports on every push:
//
//   Blocked aria-hidden on an element because its descendant retained focus.
//   Element with focus: <button.g-row g-row--tappable>
//   Ancestor with aria-hidden: <div class="ion-page g-page ion-page-hidden">
//
// A focus trapped in a hidden page is unreachable to assistive tech and to the
// keyboard path (focus resumes inside a page that no longer exists visually).
// One blur here covers every route, instead of per-page lifecycle handlers.
import { samePage } from "./samePage.js"

export function releaseFocusOnLeave(router) {
	router.beforeEach((to, from) => {
		// A navigation that stays on the page (a query change, or Back redirected onto the page by
		// sheetGuard.js) hides nothing, so focus stays where it is: the sheet's opener after Back.
		if (samePage(to, from)) return
		document.activeElement?.blur?.()
	})
}

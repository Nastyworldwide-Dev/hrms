// Remembering that an update offer was put away — PER BUILD, not for a period.
//
// THE BUG THIS FIXES, reported 23 September 2026: "the new version is still
// popping every time". Dismissing the bar only flipped a ref in the component.
// The waiting service worker stayed waiting, so the next load registered it
// again, `onNeedRefresh` fired again, and the bar came back — on every single
// reload, forever, until the employee happened to tap Reload.
//
// WHY NOT A COOLDOWN, which is what the install prompt uses. A time window is
// right there: the app is installable for as long as it is not installed, so
// "ask again in 30 days" is the only sensible shape. An update is the opposite
// — it is a specific build, it stops being relevant the moment a newer one
// lands, and a 30-day silence would hide a genuinely urgent fix.
//
// So the memory is the BUILD'S OWN IDENTITY. Put this one away and it stays
// away; ship another and the bar comes back the first time, because the key no
// longer matches.
//
// Pure, and split out from the component for the same reason
// installPromptMemory is: the decision is worth testing without a DOM, and a
// component that owns both the rule and the storage has neither tested.

export const UPDATE_DISMISS_KEY = "hrms:update-prompt-dismissed"

/**
 * The stable identity of a waiting build.
 *
 * Workbox stamps its generated service worker URL with a revision
 * (`/sw.js?__WB_REVISION__=abc123`), which changes on every build and only on
 * a build — exactly the property a per-build key needs. Falling back to the
 * whole URL is safe: on a site without the revision parameter the URL is
 * constant, so the offer is dismissed once and returns when a NEW worker
 * replaces the old one, which is still better than every load.
 *
 * @param {ServiceWorkerRegistration|null|undefined} registration
 * @returns {string|null} a key for this waiting build, or null when nothing waits
 */
export function waitingBuildId(registration) {
	const worker = registration?.waiting || registration?.installing
	const url = worker?.scriptURL
	if (typeof url !== "string" || !url) return null
	// The revision alone when there is one — the origin and path are noise, and
	// an app moved behind a different path is still the same build.
	const revision = /__WB_REVISION__=([^&]+)/.exec(url)
	return revision ? revision[1] : url
}

/**
 * Should the offer be shown for this build?
 *
 * @param {string|null} buildId   from waitingBuildId()
 * @param {string|null} dismissed the stored value
 * @returns {boolean}
 */
export function shouldOfferUpdate(buildId, dismissed) {
	// No identifiable build means we cannot remember a dismissal for it, and
	// the update itself is real — so offer it. Failing closed here would mean
	// an employee stranded on a broken build with no way to move, which is the
	// worse half of the rule this component balances.
	if (!buildId) return true
	return dismissed !== buildId
}

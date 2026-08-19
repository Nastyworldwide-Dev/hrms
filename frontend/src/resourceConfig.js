// MUST be main.js's FIRST import — this is load-bearing, not style.
//
// frappe-ui fires `auto: true` resources SYNCHRONOUSLY inside createResource
// (resources.js: `if (options.auto) out.fetch()`), and a resource declared at
// module scope therefore fetches while the import graph is still evaluating —
// BEFORE any code in main.js's body has run. Its fetch resolves
// `options.resourceFetcher || getConfig('resourceFetcher') || request`, and
// with the config not yet set it falls back to the BARE `request`, which
// never prefixes `/api/method/` and defaults to GET.
//
// That is exactly what took the Team feature down in production on
// 2026-08-19: SideNav (entry chunk) imports data/team.js, whose three
// auto resources fired first and hit
//   GET https://<site>/hrms.api.team.has_team  ->  404 (an HTML page)
// so has_team / is_approver / get_managers failed for every fresh session
// and the Team page + Team tabs vanished — while anyone with an old
// localStorage cache kept a stale `true` and saw no problem.
//
// Evaluating the config in a module imported FIRST closes the race for every
// module-scope resource, present and future. ES module evaluation order is
// depth-first in source order, so this module completes before App.vue's
// import graph ever evaluates.
//
// Wrapped, never raw: this is the one seam every resource in the app passes
// through, so it is the only place a failure can be reported once instead of
// in seventeen templates. See utils/loudRequest.js for why that matters.
import { setConfig, frappeRequest } from "frappe-ui"
import { makeLoudRequest } from "@/utils/loudRequest"

// The only resources the LOGIN PAGE itself needs — both are allow_guest on
// the server. Everything else the app declares assumes a session.
const GUEST_URLS = new Set([
	"hrms.api.system_settings.get_user_pass_login_disabled",
	"hrms.api.oauth.oauth_providers",
])

// Guest gate, observed live on 2026-08-19: the module-scope auto resources
// fire on the LOGIN page too, the server rightly answers 403 for a Guest, and
// the loud-error seam then toasts "not permitted" over the login form —
// correct plumbing, wrong audience. A Guest's non-login resources are simply
// never sent: the returned promise stays pending, the resource stays
// `loading`, nothing toasts. Correctness after login comes from
// data/session.js, which performs a FULL page load on success so every
// module-scope resource re-evaluates with the session cookie present
// (pinned together with this file by login-guest-quiet.test.mjs).
//
// The cookie is read inline, never via data/session.js: importing that here
// would pull the data modules into this file's import graph and re-create the
// very evaluate-before-config race this module exists to close.
function guestQuiet(fetcher) {
	return (options) => {
		const cookies = new URLSearchParams(document.cookie.split("; ").join("&"))
		const user = cookies.get("user_id")
		if ((!user || user === "Guest") && !GUEST_URLS.has(options.url)) {
			console.info("[resourceConfig] guest session — holding", options.url)
			return new Promise(() => {})
		}
		return fetcher(options)
	}
}

setConfig("resourceFetcher", guestQuiet(makeLoudRequest(frappeRequest)))

import { toast } from "frappe-ui"

// Every request the PWA makes, made audible.
//
// Components are written `v-if="resource.data"`. A resource that errored has no
// `.data`, so the component renders NOTHING — not an error, not an empty state,
// nothing. Seventeen components share that shape, which means a missing argument,
// an unmirrored doctype and a dropped connection all look identical on screen: a
// blank rectangle.
//
// That is why four separate faults arrived as "the attendance calendar is
// missing" and sat unexplained for a week. The bug was never hard; finding out
// WHICH bug it was took a week because nothing on screen distinguished them.
//
// So failure gets announced here, once, at the single seam every resource passes
// through (`setConfig("resourceFetcher", ...)` in main.js) rather than in
// seventeen templates that would each have to remember.

const REPEAT_WINDOW_MS = 5000
const recentlyReported = new Map()

// Handled by the router's redirect to /login, so a toast would be noise on top of
// a navigation the user can already see — and it fires in bursts as every mounted
// resource discovers the session is gone at the same moment.
const SILENT_EXCEPTIONS = new Set(["AuthenticationError", "SessionExpired", "SessionStopped"])

// Endpoints whose failure is not a page-level event. A link-picker typeahead is
// the case this exists for: on the expense claim form it 403s for Account,
// Currency, Branch and Location, and each one raised a "Could not load —
// Insufficient Permission for Account" toast, anchored bottom-centre, directly
// ON TOP of the screen's only submit button. Two defects in one: the primary
// action was covered, and raw backend vocabulary with a capitalised doctype
// name was shown to an employee filing a claim.
// The control's own empty state is the right feedback for a lookup that
// returned nothing. Still logged to the console — silent to the user, never to
// a developer.
//
// get_attachments is the same shape one layer up: a detail form fires it in
// PARALLEL with loading the document, so when the caller cannot READ that
// document (a boss taps a notification for a request that is not routed to him)
// BOTH 403 at once. The document failure already draws FormView's "Could not
// open this — you may not have access" screen WITH a Back button; the parallel
// get_attachments failure only piled a second toast of raw backend vocabulary
// ("...does not have permission... Leave Application") on top of it. That toast
// was the visible half of the "stuck on a permission error" report. Silence it:
// the form's own error state is the single, escapable feedback.
const SILENT_ENDPOINTS = new Set(["frappe.desk.search.search_link", "hrms.api.get_attachments"])

function endpointOf(options) {
	const url = options?.url || "unknown endpoint"
	return url.replace(/^\/api\/method\//, "")
}

function firstMessage(error) {
	return error?.messages?.[0] || error?.message || "Request failed"
}

function isRepeat(endpoint, now) {
	const last = recentlyReported.get(endpoint)
	recentlyReported.set(endpoint, now)
	return last !== undefined && now - last < REPEAT_WINDOW_MS
}

/**
 * Wraps a frappe-ui request function so failures are logged and surfaced.
 *
 * `notify` and `now` are injectable so this is testable without a browser.
 * The wrapped function ALWAYS rethrows: `createResource`'s own `onError`
 * callbacks, and every `try`/`catch` around a `.submit()`, still run exactly as
 * before. This adds a report; it does not take over handling.
 */
export function makeLoudRequest(request, { notify = toast, now = () => Date.now() } = {}) {
	return function loudRequest(options) {
		return request(options).catch((error) => {
			const endpoint = endpointOf(options)

			// Always logged, whatever it is. The console is where a developer looks
			// and it costs the user nothing — it is also the line that turns "the
			// screen is blank" into a named endpoint in one step.
			console.error("[request] failed:", endpoint, error?.exc_type || "", firstMessage(error))

			if (
				!SILENT_EXCEPTIONS.has(error?.exc_type) &&
				!SILENT_ENDPOINTS.has(endpoint) &&
				!isRepeat(endpoint, now())
			) {
				notify({
					title: "Could not load",
					text: firstMessage(error),
					icon: "alert-circle",
					position: "bottom-center",
					iconClasses: "text-red-500",
				})
			}

			throw error
		})
	}
}

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

			if (!SILENT_EXCEPTIONS.has(error?.exc_type) && !isRepeat(endpoint, now())) {
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

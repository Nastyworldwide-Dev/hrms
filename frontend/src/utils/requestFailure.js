import { isNoAccess } from "./sessionLost.js"
import { noServerAnswer, phoneOffline, firstMessage } from "./refusalText.js"

// What a failed request deserves, decided in one place: stay silent, say "you can't open this",
// say "something didn't load", or say nothing because the same endpoint was just reported.
// Split out of loudRequest.js (alpha.41 S12): that file now only wires in the toast and the
// session cookie; everything here takes them as arguments, so it runs under plain node and bun.
// The words of a refusal live in refusalText.js, which returns text and nothing else; the toast
// (components/glass/toast.js) is the one place that escapes it.

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
// submit_late_checkout: the dialog catches the rejection and shows "Could not
// submit" with the server's reason; a second toast here — titled as if a page
// failed to LOAD — is what HR photographed when a submission was refused.
const SILENT_ENDPOINTS = new Set([
	"frappe.desk.search.search_link",
	"hrms.api.get_attachments",
	"hrms.api.remote_checkin.submit_late_checkout",
	// CheckInPanel presents the failed punch and restores its retry controls.
	"hrms.api.remote_checkin.punch",
	// RequestActionSheet's onActionError shows "Error" with the server's reason;
	// managers photographed this seam's toast stacked on top of it, the same
	// sentence twice, on every refused Approve.
	"hrms.api.approval.decide",
	// Same sheet, same onActionError, for the plain submit/cancel transition.
	"hrms.api.approval.finalize",
	// The claim is already saved and its create toast shown; a warning that
	// could not be fetched is logged by utils/nearDuplicateWarning.js, not
	// reported as a page that failed to load.
	"hrms.api.near_duplicate_expenses",
	// Home's Announcements block shows its own "didn't load" banner in place;
	// the toast on top was the same failure reported twice (audit F-6).
	"hrms.api.announcements.home_announcements",
	// Writes whose callers already toast the server's own reason
	// (composables/index.js, composables/workflow.js). The generic "didn't
	// load" on top was wrong for a write and said it twice (review of a3fe4b4a4).
	"hrms.api.upload_base64_file",
	"hrms.api.delete_attachment",
	"frappe.model.workflow.apply_workflow",
	// TicketDetail.send toasts "Reply not sent" with the server's reason. A refused
	// reply (PermissionError) is no longer toasted here at all (L1a), so without its
	// own toast the person would have heard nothing.
	"hrms.api.helpdesk.reply",
])

// A refusal the screen draws itself ("You can't open this." in FormView / ResourceError,
// both marked data-no-access): no toast goes on top of its sentence. The screen renders
// after the request settles, so the check waits one frame before deciding.
function noAccessDrawn(options) {
	if (options?.noAccessShown) return true
	return (
		typeof document !== "undefined" &&
		Boolean(document.querySelector?.(":not(.ion-page-hidden) [data-no-access]"))
	)
}

function endpointOf(options) {
	const url = options?.url || "unknown endpoint"
	return url.replace(/^\/api\/method\//, "")
}

function isRepeat(endpoint, now) {
	const last = recentlyReported.get(endpoint)
	recentlyReported.set(endpoint, now)
	return last !== undefined && now - last < REPEAT_WINDOW_MS
}

/**
 * What this failure is: "silent" (reported elsewhere, or the offline banner says it), "refused"
 * (a refusal of THIS page from a person still signed in), "repeat" (this endpoint was reported
 * inside the window) or "load" (say it). `signedIn` and `now` are functions: each is read only
 * when the checks before it let it be, and only a failure that goes on to be reported starts the
 * repeat window, so a refusal never uses it up.
 */
function classifyFailure(error, { endpoint, signedIn, now }) {
	const silenced =
		SILENT_EXCEPTIONS.has(error?.exc_type) ||
		SILENT_ENDPOINTS.has(endpoint) ||
		// offline: the banner already says it (an unreachable server while online
		// has no banner, so it still gets the toast)
		(noServerAnswer(error) && phoneOffline())
	if (silenced) return "silent"
	if (isNoAccess(error, { signedIn: signedIn() })) return "refused"
	return isRepeat(endpoint, now()) ? "repeat" : "load"
}

// Failures this seam has already logged (and toasted, unless silent). frappe-ui
// fires `auto: true` fetches with a bare `out.fetch()` that nobody awaits, and
// its handleError always rethrows — so every failed auto-load ALSO reached the
// browser as an unhandled rejection (`pageerror: …DoesNotExistError` on every
// missing document, crawl of 15 Sep 2026), on top of the ResourceError the page
// drew. The rejection itself is kept: an awaited `.submit()` still throws to its
// caller. Only the browser's "nobody caught this" report is cancelled, and only
// for an error that is provably already on record here.
const reported = new WeakSet()

/** `unhandledrejection` listener: cancel the report for a failure already reported above. */
export function swallowReportedRejection(event) {
	const reason = event?.reason
	if (reason === null || typeof reason !== "object" || !reported.has(reason)) return
	console.info("[request] unawaited failure already reported:", reason?.exc_type || "")
	event.preventDefault()
}

/**
 * Wraps a frappe-ui request function so failures are logged and surfaced.
 *
 * `notify`, `now` and `signedIn` are injected (loudRequest.js supplies the real toast, clock and
 * session cookie), so this is testable without a browser.
 * The wrapped function ALWAYS rethrows: `createResource`'s own `onError`
 * callbacks, and every `try`/`catch` around a `.submit()`, still run exactly as
 * before. This adds a report; it does not take over handling.
 */
export function makeFailureReporter(request, { notify, now, signedIn }) {
	return function loudRequest(options) {
		return request(options).catch((error) => {
			const endpoint = endpointOf(options)

			// Always logged, whatever it is. The console is where a developer looks
			// and it costs the user nothing — it is also the line that turns "the
			// screen is blank" into a named endpoint in one step.
			console.error("[request] failed:", endpoint, error?.exc_type || "", firstMessage(error))

			const verdict = classifyFailure(error, { endpoint, signedIn, now })
			if (verdict === "refused") {
				// A refusal from a person still signed in ("this is not yours to open"). A screen
				// that draws "You can't open this." itself (FormView, ResourceError: data-no-access)
				// gets no toast on top; any other screen gets that plain sentence as a toast, never
				// "didn't load ... try again" (L1a and its review, alpha.38). Decided after a frame,
				// once the screen has drawn. A refusal never uses up the repeat window, so a later
				// real failure on the same endpoint is still reported. A session that ENDED is not
				// a refusal (isNoAccess) and goes on to the generic path, then the reload to Login.
				const later =
					typeof requestAnimationFrame === "function"
						? requestAnimationFrame
						: (fn) => setTimeout(fn, 0)
				later(() => {
					if (!noAccessDrawn(options))
						notify({
							title: "You can't open this.",
							text: "It is not shared with you.",
							variant: "error",
						})
				})
			} else if (verdict === "load") {
				// Plain words only (audit F-6): the server's sentence names doctypes,
				// roles and e-mail addresses. It is in the console line above; the
				// screen that owns the data shows its own "didn't load" in place.
				notify({
					title: "Something didn't load",
					text: "Try again in a moment.",
					variant: "error",
				})
			}

			if (error !== null && typeof error === "object") reported.add(error)
			throw error
		})
	}
}

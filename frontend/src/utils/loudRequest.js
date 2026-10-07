import { gToast } from "@/components/glass/toast"
import { isNoAccess } from "@/utils/sessionLost"
import { sessionUser } from "@/utils/personalCache"

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

// Shared with the forms: a refused create/update must show the server's reason
// ("Insufficient leave balance", "outside leave allocation period"), not a
// generic "Error creating X" — which is what an employee reported as "unknown
// error" when their leave application was refused (15 Sep 2026).
// The toast renders `text` with v-html, and server refusals carry Desk links
// and <strong> markup: plain text only, so an employee never sees a live
// link to a Desk page they cannot open.
// `fallback` is the caller's own wording for a failure that carries no
// server message at all (a network drop, a thrown TypeError).
// A request that never got a server answer: the browser says "Failed to fetch"
// (Chrome), "NetworkError ..." (Firefox) or "Load failed" (Safari). That is the
// phone being offline OR the server being down/restarting, so the words depend
// on navigator.onLine (owner ruling R4, 6 Oct 2026: a clear failure, no queue;
// review: "offline" was wrong for a server that was simply unreachable).
function noServerAnswer(error) {
	if (!error || error.exc_type || error.messages?.length) return false
	return /failed to fetch|networkerror|network request failed|load failed/i.test(
		String(error.message || "")
	)
}

function phoneOffline() {
	return typeof navigator !== "undefined" && navigator.onLine === false
}

/** A form's save failed: what to say after "Could not save this …". Only form-save
 *  sites use it, because only there is something typed still on screen. A request
 *  can leave before the connection drops, so it says "may not have been sent". */
export function saveFailedSentence(error, fallback) {
	if (!noServerAnswer(error)) return firstMessage(error, fallback)
	return phoneOffline()
		? "You are offline, so it may not have been sent. What you typed is still here."
		: "The server could not be reached, so it may not have been sent. What you typed is still here."
}

export function firstMessage(error, fallback = "Request failed") {
	if (noServerAnswer(error))
		return phoneOffline() ? "No connection." : "Could not reach the server."
	const message = error?.messages?.[0] || error?.message || fallback
	return (
		String(message)
			// a break between parts stays a space ("Line one<br>Line two"); inline tags just go
			.replace(/<br\s*\/?>|<\/(p|li|div)>/gi, " ")
			.replace(/<[^>]*>/g, "")
			// an unclosed tag at the end ("x <img onerror=...") is dropped, and any < or > left
			// becomes its look-alike: the toast renders with v-html, so this can never be markup
			.replace(/<[^>]*$/, "")
			.replace(/</g, "‹")
			.replace(/>/g, "›")
			.replace(/\s+/g, " ")
			.trim()
	)
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
export function makeLoudRequest(request, { notify = gToast, now = () => Date.now() } = {}) {
	return function loudRequest(options) {
		return request(options).catch((error) => {
			const endpoint = endpointOf(options)

			// Always logged, whatever it is. The console is where a developer looks
			// and it costs the user nothing — it is also the line that turns "the
			// screen is blank" into a named endpoint in one step.
			console.error("[request] failed:", endpoint, error?.exc_type || "", firstMessage(error))

			const silenced =
				SILENT_EXCEPTIONS.has(error?.exc_type) ||
				SILENT_ENDPOINTS.has(endpoint) ||
				// offline: the banner already says it (an unreachable server while online
				// has no banner, so it still gets the toast)
				(noServerAnswer(error) && phoneOffline())
			if (!silenced && isNoAccess(error, { signedIn: Boolean(sessionUser()) })) {
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
			} else if (!silenced && !isRepeat(endpoint, now())) {
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

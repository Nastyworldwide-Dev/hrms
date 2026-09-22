// What broke, for the sentence this exists to answer (pre-2.0 R4, §16).
//
// "I submitted it yesterday and my manager cannot see it." Today there is
// nothing to look at: no record of the error the employee saw, no way to tell
// which build they were running, nothing that survives the tab being closed.
// The console has it for as long as the page lives, and the page is the one
// thing that does not.
//
// WHAT THIS IS NOT. Not Sentry, not a service, not a network call. The server
// is Frappe and it already has an Error Log; anything worth keeping goes there
// through the API the app already speaks, and everything else is a console
// line with enough context to be searched. Adding a telemetry vendor to an
// internal HR app for forty employees is a dependency, an egress path and a
// data-protection question in exchange for a dashboard nobody would open.
//
// WHAT IT MUST NEVER DO. §16: never log passwords, tokens, salary or personal
// data. That is enforced HERE, by redacting before anything is written —
// callers being careful is not a mechanism. And reporting cannot itself
// throw: a reporter that fails inside an error handler takes the page down
// and loses the thing it was reporting.

/** Stamped at build time by vite.config.js — see `define`. */
const BUILD = typeof __APP_BUILD__ === "string" ? __APP_BUILD__ : "dev"

//: Keys whose VALUE never appears in a report, whatever the shape around it.
//: Matched loosely on purpose: `new_password`, `api_key`, `basic_salary` and
//: `ctc` are all the same class, and a list of exact names ages badly.
const REDACT =
	/(pass(word)?|secret|token|api[_-]?key|auth|cookie|session|salary|ctc|bank|nric|ic[_-]?no|passport)/i

/** Replace the value of any key that looks sensitive, at any depth. */
function redact(value, depth = 0) {
	if (depth > 4 || value == null) return value
	if (Array.isArray(value)) return value.map((v) => redact(v, depth + 1))
	if (typeof value !== "object") return value
	const out = {}
	for (const [key, inner] of Object.entries(value)) {
		out[key] = REDACT.test(key) ? "[redacted]" : redact(inner, depth + 1)
	}
	return out
}

/** The context every report carries, so one can be matched to a person and a build. */
function envelope() {
	let user = null
	try {
		// The session cookie, not a resource: this runs from an error handler,
		// possibly before the app has finished starting.
		user = new URLSearchParams(document.cookie.split("; ").join("&")).get("user_id")
	} catch {
		/* a blocked cookie jar must not break the report */
	}
	return {
		build: BUILD,
		at: new Date().toISOString(),
		route: typeof location === "undefined" ? null : location.hash || location.pathname,
		// Who, not what: the login identifies the person for support without
		// carrying anything about them.
		user: user && user !== "Guest" ? user : null,
		online: typeof navigator === "undefined" ? null : navigator.onLine,
	}
}

/**
 * Record a failure. Never throws, never returns anything a caller must handle.
 * `where` is a short stable label ("leave.submit"), `detail` any extra context.
 */
export function report(where, error, detail = null) {
	try {
		const context = { ...envelope(), where, ...(detail ? { detail: redact(detail) } : {}) }
		console.error(`[diagnostics] ${where}`, error, context)
	} catch {
		/* a reporter that throws inside an error handler loses the page AND the
		   error it was reporting; there is nothing useful to do here. */
	}
}

/**
 * Attach the three seams a browser offers. Idempotent — calling it twice
 * attaches one set, because a doubled handler doubles every report.
 */
let installed = false
export function installDiagnostics(app) {
	if (installed || typeof window === "undefined") return
	installed = true

	window.addEventListener("error", (event) => {
		// A failed <img> or <script> fires this too, with no `error` object;
		// those are noise, not failures anybody investigates.
		if (!event.error) return
		report("window.error", event.error, { message: event.message })
	})

	window.addEventListener("unhandledrejection", (event) => {
		// `resourceConfig` already cancels the rejections it has itself
		// reported (loudRequest's swallowReportedRejection), so what reaches
		// here is genuinely unhandled.
		if (event.defaultPrevented) return
		report("unhandledrejection", event.reason)
	})

	if (app) {
		const previous = app.config.errorHandler
		app.config.errorHandler = (error, instance, info) => {
			report("vue.render", error, { info })
			// Chain rather than replace: Vue's default logs to the console, and
			// a handler that silently swallows makes a component that throws
			// look like a component that rendered nothing.
			if (typeof previous === "function") previous(error, instance, info)
			else console.error(error)
		}
	}

	console.info(`[diagnostics] build ${BUILD}`)
}

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

//: A value's own SHAPE, for the cases a key name cannot catch. Key matching
//: only works when the caller named the field; `{ data: { value: <bank
//: account> } }` defeats it entirely (security review of b7a23bc7c). These are
//: the shapes worth refusing on sight in this app.
const LOOKS_SECRET = [
	/^[A-Za-z0-9_-]{20,}$/, // an opaque token: long, no spaces, no punctuation
	/\b\d{10,19}\b/, // an account or card number
	/^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/, // an address
	/\b\d{6}-\d{2}-\d{4}\b/, // a Malaysian NRIC
]

/** Replace anything that looks sensitive by its key OR by its own shape. */
function redact(value, depth = 0) {
	// FAIL CLOSED past the limit. This used to return the value raw, which
	// meant the one case the limit exists for — a body nested deeper than
	// expected — was the case it stopped protecting. A Frappe error body
	// reaches depth 5 in ordinary use.
	if (depth > 4) return "[too deep]"
	if (value == null) return value
	if (Array.isArray(value)) return value.map((v) => redact(v, depth + 1))
	if (typeof value === "string")
		return LOOKS_SECRET.some((r) => r.test(value)) ? "[redacted]" : value
	if (typeof value !== "object") return value
	// An Error carries its interesting parts on the prototype and as
	// non-enumerable properties, so Object.entries alone returns {}.
	if (value instanceof Error) {
		return redact({ name: value.name, message: value.message, ...value }, depth)
	}
	// A Map or a Set is not traversable by Object.entries either, and its
	// contents are exactly as unknown as an object's.
	if (value instanceof Map || value instanceof Set) return "[unreadable]"
	const out = {}
	for (const [key, inner] of Object.entries(value)) {
		out[key] = REDACT.test(key) ? "[redacted]" : redact(inner, depth + 1)
	}
	return out
}

/** An error's stack WITHOUT its first line, which is the message repeated. */
function frames(error) {
	const stack = error?.stack
	if (typeof stack !== "string") return ""
	const lines = stack.split("\n")
	// V8 puts "Name: message" first and indents every frame; Firefox has no
	// header line at all. Keeping only indented/`@`-shaped lines is true of
	// both and cannot accidentally keep a message.
	return lines.filter((line) => /^\s+at\s|@/.test(line)).join("\n")
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
		// The ERROR goes through redaction too. It used to be logged raw, on the
		// assumption that an Error is a message and a stack — but in this app a
		// failure arrives from Frappe with the server's sentence in its message
		// and the response hanging off it as a property, so the most ordinary
		// error shape here was the one that bypassed the filter entirely
		// (security review of b7a23bc7c, CRITICAL).
		//
		// The stack's FRAMES only. A stack's first line is the message — so
		// logging the stack raw put the sentence straight back in the log,
		// redacted object and all, which is what the first attempt at this fix
		// did. The frames themselves are file names and line numbers from our
		// own bundle and carry nothing about the employee; they are also the
		// only thing that says WHERE the failure happened, and a report nobody
		// can act on is the same as no report.
		console.error(`[diagnostics] ${where}`, redact(error), context, frames(error))
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

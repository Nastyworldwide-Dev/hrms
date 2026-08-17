// Guest endpoint — the user has no session yet, so this posts directly
// instead of going through frappe-ui's session-bound call().
const RESET_PASSWORD_URL = "/api/method/frappe.core.doctype.user.user.reset_password"

export async function sendPasswordResetLink(email, fetcher = globalThis.fetch) {
	const headers = {
		"Content-Type": "application/json",
		Accept: "application/json",
	}

	// Guest does NOT mean exempt. `hrms/www/hrms.py` renders this page through
	// `frappe.sessions.get_csrf_token()`, which GENERATES a token for the guest
	// session — and a generated token is exactly what arms frappe's check
	// (`auth.py`: it returns early only when no token was saved, or the header
	// matches, or the referrer is in an allowlist that is empty by default).
	//
	// So loading the login page is what makes a header-less POST from it fail:
	// 400 CSRFTokenError, thrown before `reset_password` runs a single line.
	// Three other raw fetches in this app already send the header; this one was
	// written without it, which is why Forgot Password could never send anything.
	if (globalThis.csrf_token) headers["X-Frappe-CSRF-Token"] = globalThis.csrf_token
	else
		console.warn("[ResetPassword] no csrf_token on the page — expect 400 from", RESET_PASSWORD_URL)

	const res = await fetcher(RESET_PASSWORD_URL, {
		method: "POST",
		headers,
		body: JSON.stringify({ user: email }),
	})

	// Current frappe v15 always answers 200 with a generic message so unknown
	// emails are indistinguishable (CWE-204 anti-enumeration); pre-hardening
	// releases answered 404 for unknown users. Treat both the same here so
	// this client never becomes an enumeration oracle — the dialog's neutral
	// "if this email is registered" copy covers both outcomes.
	if (res.ok || res.status === 404) return true

	console.warn("[ResetPassword] request failed:", RESET_PASSWORD_URL, res.status)
	// 429 is frappe's @rate_limit status; it fires for existing and unknown
	// emails alike, so surfacing it leaks nothing.
	if (res.status === 429) {
		throw new Error("Too many reset requests — please try again later")
	}
	throw new Error("Could not send the reset email. Please try again.")
}

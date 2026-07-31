// Guest endpoint — the user has no session yet, so this posts directly
// instead of going through frappe-ui's session-bound call().
const RESET_PASSWORD_URL = "/api/method/frappe.core.doctype.user.user.reset_password"

export async function sendPasswordResetLink(email, fetcher = globalThis.fetch) {
	const res = await fetcher(RESET_PASSWORD_URL, {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
			Accept: "application/json",
		},
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

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

	if (res.ok) return true

	// Frappe answers 404 for an unknown user and 417/429 when the hourly
	// reset limit is hit — surface those as actionable messages, everything
	// else as a generic failure.
	console.warn("[ResetPassword] request failed:", RESET_PASSWORD_URL, res.status)
	if (res.status === 404) {
		throw new Error("No account found with this email address")
	}
	if (res.status === 417 || res.status === 429) {
		throw new Error("Too many reset requests — please try again later")
	}
	throw new Error("Could not send the reset email. Please try again.")
}

// A sheet that never stops loading reports itself (alpha.60: Aiman's OT and
// Medical Leave sat grey on a senior's phone and never reproduced here). Plain
// fetch, not a frappe-ui resource: the resource fetcher can be what holds it.
// ceiling: 10 s before a load counts as stuck; upgrade: lower it if live logs show real loads finish much sooner
export const STUCK_LOAD_MS = 10000

export async function reportStuckLoad({ doctype, name, ms, inFlight }) {
	const cookies = new URLSearchParams(document.cookie.split("; ").join("&"))
	const user = cookies.get("user_id")
	const headers = { "X-Frappe-Site-Name": window.location.hostname }
	if (window.csrf_token) headers["X-Frappe-CSRF-Token"] = window.csrf_token
	console.warn("[stuckLoad]", doctype, name, ms, "ms, in flight:", inFlight)
	try {
		await fetch("/api/method/hrms.api.report_stuck_load", {
			method: "POST",
			headers,
			body: new URLSearchParams({
				doctype,
				name,
				ms: String(ms),
				in_flight: inFlight ? "1" : "0",
				has_user_cookie: user && user !== "Guest" ? "1" : "0",
			}),
		})
	} catch (error) {
		console.warn("[stuckLoad] report not sent:", error?.message)
	}
}

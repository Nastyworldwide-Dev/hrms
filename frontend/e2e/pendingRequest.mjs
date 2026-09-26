// A synthetic pending leave request, so an approver has something to open.
// Filed as the W0 employee through the app's own API and deleted afterwards;
// the sheet audits use it to reach the approval sheet (alpha.11: the two
// sheets the audits never opened were the calendar day and the approval).
import { BASE, PW } from "./screens.mjs"

export async function withPendingLeave(browser, run) {
	const ctx = await browser.newContext()
	await ctx.request.post(`${BASE}/api/method/login`, { form: { usr: "nadi.w0.employee@example.invalid", pwd: PW } })
	const page = await ctx.newPage()
	await page.goto(`${BASE}/hrms/home`, { waitUntil: "networkidle" })
	const csrf = await page.evaluate(() => window.csrf_token || window.frappe?.csrf_token)
	const headers = { "X-Frappe-CSRF-Token": csrf }
	const me = (await (await ctx.request.get(`${BASE}/api/method/hrms.api.get_current_employee_info`)).json()).message
	const res = await ctx.request.post(`${BASE}/api/method/frappe.client.insert`, {
		headers,
		data: { doc: { doctype: "Leave Application", employee: me.name, leave_type: "Nadi W0 Annual", from_date: "2026-12-14", to_date: "2026-12-14", description: "ZZAUDIT sheet", status: "Open" } },
	})
	const name = (await res.json()).message?.name
	try {
		return await run(name)
	} finally {
		// The app's own Withdraw (staff have no delete right on a request — a
		// frappe.client.delete here 403'd silently and left the leave behind,
		// which moved the approver's pages in the next audit run).
		if (name) {
			const gone = await ctx.request.post(`${BASE}/api/method/hrms.api.withdraw_request`, {
				headers,
				data: { doctype: "Leave Application", name },
			})
			if (!gone.ok()) console.warn(`[pendingRequest] could not withdraw ${name}: ${gone.status()}`)
		}
		await ctx.close()
	}
}

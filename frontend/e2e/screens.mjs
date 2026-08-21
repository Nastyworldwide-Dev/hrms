// The screen list, shared by every render-time gate and by the audit capture
// script (docs/glass/audit/capture.mjs). ONE list: a route that is added here
// is audited, a11y-checked and visual-regression-checked without further work,
// and a route added anywhere else is caught by none of them.

export const BASE = process.env.HRMS_E2E_URL || "http://localhost:8080"
export const USER = process.env.HRMS_E2E_USER || "nurul.aisyah@nastyworldwide.com"
export const PW = process.env.AUDIT_PW || process.env.HRMS_E2E_PW || ""

/** Log in over the API and return a storageState for reuse across contexts. */
export async function login(browser) {
	const ctx = await browser.newContext()
	const res = await ctx.request.post(`${BASE}/api/method/login`, {
		form: { usr: USER, pwd: PW },
	})
	if (res.status() !== 200) {
		await ctx.close()
		throw new Error(`login failed: ${res.status()} — set AUDIT_PW`)
	}
	const state = await ctx.storageState()
	await ctx.close()
	return state
}

/** Newest document id for a doctype, or null when the site has none. */
async function firstId(request, doctype) {
	try {
		const r = await request.get(
			`${BASE}/api/method/frappe.client.get_list?doctype=${encodeURIComponent(doctype)}` +
				`&limit_page_length=1&order_by=modified%20desc`
		)
		return (await r.json())?.message?.[0]?.name ?? null
	} catch {
		return null
	}
}

/**
 * Resolve the screen list against whatever this site actually holds. Detail
 * routes need a real document; when the site has none the screen is dropped
 * rather than rendered as a 404, so a thin site reports fewer screens instead
 * of a wall of false failures.
 */
export async function screens(request) {
	const id = {
		leave: await firstId(request, "Leave Application"),
		attReq: await firstId(request, "Attendance Request"),
		shiftReq: await firstId(request, "Shift Request"),
		shiftAssign: await firstId(request, "Shift Assignment"),
		claim: await firstId(request, "Expense Claim"),
		issue: await firstId(request, "Employee Issue"),
		ot: await firstId(request, "OT Request"),
		rlc: await firstId(request, "Replacement Leave Claim"),
		sop: await firstId(request, "SOP Document"),
	}
	const S = (slug, path, anon = false) => ({ slug, path, anon })
	return [
		S("login", "/login", true),
		S("forgot-password", "/forgot-password", true),
		S("home", "/home"),
		S("dash-attendance", "/dashboard/attendance"),
		S("dash-leaves", "/dashboard/leaves"),
		S("dash-expense-claims", "/dashboard/expense-claims"),
		S("dash-kpi", "/dashboard/kpi"),
		S("issues", "/issues"),
		S("issues-new", "/issues/new"),
		S("issues-detail", id.issue && `/issues/${id.issue}`),
		S("hr-issue-board", "/hr/issues"),
		S("sop", "/sop"),
		S("sop-detail", id.sop && `/sop/${id.sop}`),
		S("team", "/team"),
		S("more", "/more"),
		S("profile", "/profile"),
		S("notifications", "/notifications"),
		S("settings", "/settings"),
		S("change-password", "/change-password"),
		S("hr-contacts", "/hr-contacts"),
		S("remote-approvals", "/remote-approvals"),
		S("invalid-employee", "/invalid-employee"),
		S("attendance-requests", "/attendance-requests"),
		S("attendance-requests-new", "/attendance-requests/new"),
		S("attendance-requests-detail", id.attReq && `/attendance-requests/${id.attReq}`),
		S("shift-requests", "/shift-requests"),
		S("shift-requests-new", "/shift-requests/new"),
		S("shift-requests-detail", id.shiftReq && `/shift-requests/${id.shiftReq}`),
		S("shift-assignments", "/shift-assignments"),
		S("shift-assignments-detail", id.shiftAssign && `/shift-assignments/${id.shiftAssign}`),
		S("employee-checkins", "/employee-checkins"),
		S("expense-claims", "/expense-claims"),
		S("expense-claims-new", "/expense-claims/new"),
		S("expense-claims-detail", id.claim && `/expense-claims/${id.claim}`),
		S("leave-applications", "/leave-applications"),
		S("leave-applications-new", "/leave-applications/new"),
		S("leave-applications-detail", id.leave && `/leave-applications/${id.leave}`),
		S("ot-requests", "/ot-requests"),
		S("ot-requests-new", "/ot-requests/new"),
		S("ot-requests-detail", id.ot && `/ot-requests/${id.ot}`),
		S("replacement-leave", "/replacement-leave"),
		S("replacement-leave-new", "/replacement-leave/claims/new"),
		S("replacement-leave-detail", id.rlc && `/replacement-leave/claims/${id.rlc}`),
	].filter((s) => s.path)
}

/** Settle the SPA: route resolved, data in, animations done. */
export async function settle(page) {
	await page.waitForLoadState("networkidle").catch(() => {})
	await page.waitForTimeout(2200)
}

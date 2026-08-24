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
	// Wait for WEBFONTS. §4.1 self-hosts Inter/Inter Tight with font-display:
	// swap, so text paints in a fallback face first and swaps when the real one
	// arrives. Without this, one render in five caught the fallback: the login
	// logo's "HR" came out at a different weight, 28 differing pixels, which is
	// indistinguishable from a regression and sits right on top of the smallest
	// real change this gate needs to catch (34px).
	// document.fonts.ready alone is NOT enough: it resolves for the faces already
	// requested, and a face is only requested once something needs it. The login
	// logo kept flapping between a synthesised and a real bold. Ask for every
	// face the page actually uses, then wait again.
	await page
		.evaluate(async () => {
			await document.fonts.ready
			const faces = new Set()
			for (const el of document.querySelectorAll("*")) {
				const cs = getComputedStyle(el)
				faces.add(`${cs.fontStyle} ${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`)
			}
			await Promise.all([...faces].map((f) => document.fonts.load(f).catch(() => {})))
			await document.fonts.ready
		})
		.catch(() => {})
	await page.waitForTimeout(2200)
}

/**
 * Touch targets, HIT-TESTED rather than measured.
 *
 * getBoundingClientRect() reports the element's own box. §14.1 allows a target
 * to be expanded around a smaller visual — the token's description is literally
 * "padded out to 44px WITHOUT moving the visual" — and the app does that with
 * ::before overlays on the month steppers, the section-header links and the
 * push toggle. Measuring boxes reported all of those as failures they are not.
 * A gate with known false positives gets ignored, so this asks the browser what
 * is actually at the point instead.
 *
 * A control passes when the midpoints of its 44px-tall (and, if it is narrow,
 * 44px-wide) region resolve back to it.
 *
 * Returns [{ label, tag, box, missed }] for controls that FAIL.
 */
export async function undersizedTargets(page, min = 44) {
	return page.evaluate((MIN) => {
		const SEL = "button, a[href], [role=button], [role=tab], input, select, textarea, ion-tab-button"
		const out = []
		for (const el of document.querySelectorAll(SEL)) {
			const r = el.getBoundingClientRect()
			if (r.width < 2 || r.height < 2) continue
			const cs = getComputedStyle(el)
			if (cs.visibility === "hidden" || cs.display === "none" || cs.pointerEvents === "none") continue
			// only judge what is actually on screen
			if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) continue

			const cx = r.x + r.width / 2
			const cy = r.y + r.height / 2
			const reach = MIN / 2 - 1
            // vertical always; horizontal only when the visual is itself narrow
			const points = [[cx, cy - reach], [cx, cy + reach]]
			if (r.width < MIN) points.push([cx - reach, cy], [cx + reach, cy])

			// An overlay that covers content AT REST by design — scrolling
			// reveals it — says nothing about the occluded target's size.
			//
			// Two such overlays exist, and they need two different tests:
			//   * the floating tab bar, matched by name. It computes to
			//     position:absolute (verified), so a position-based test does
			//     NOT catch it — which is why the original named check stays.
			//   * a form's sticky Save bar, which has no stable class to name
			//     but is position:sticky.
			// Additive on purpose: dropping the named check in favour of the
			// positional one re-flagged "Request a Shift" and "View list" under
			// the tab bar on dash-attendance.
			//
			// Measured justification for the sticky case: on
			// attendance-requests-new, "Select Reason" (358x48) and the
			// Explanation textarea (358x66) are both far above the 44px
			// minimum and were flagged only because the action bar paints over
			// their lower midpoint at scrollTop 0; scrolling the form clears
			// both.
			//
			// Neither exception can mask a genuinely small control: the check
			// is positional, so an undersized target still misses at the points
			// the overlay does NOT cover. The 28 known baseline violations
			// still report with this in place.
			//
			// Same for a point off the viewport: unjudgeable, not a failure.
			const floating = document.querySelector("ion-tab-bar.g-tabbar")
			const isStickyOverlay = (node) => {
				for (let p = node; p && p !== document.body; p = p.parentElement) {
					if (p === el || el.contains(p)) return false
					if (getComputedStyle(p).position === "sticky") return true
				}
				return false
			}
			const missed = []
			for (const [x, y] of points) {
				if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) continue
				const hit = document.elementFromPoint(x, y)
				if (!hit) continue
				// the element itself, something inside it, or its own ::before overlay
				const owns = hit === el || el.contains(hit) || hit.contains(el)
				if (owns) continue
				if (floating && (hit === floating || floating.contains(hit))) continue
				if (isStickyOverlay(hit)) continue
				missed.push(`${Math.round(x)},${Math.round(y)}`)
			}
			if (missed.length) {
				out.push({
					label: (el.getAttribute("aria-label") || el.textContent || el.tagName).trim().slice(0, 40),
					tag: el.tagName.toLowerCase(),
					box: [Math.round(r.width), Math.round(r.height)],
					missed,
				})
			}
		}
		return out
	}, min)
}

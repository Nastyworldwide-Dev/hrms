import { expect, test } from "@playwright/test"

import { BASE, PW, login } from "./screens.mjs"

// "The KPI page — back and forth stuck glitch" (15 Sep). The page's setup threw
// (a watch read a const still in its temporal dead zone), so it never mounted
// its <ion-page>; Ionic's outlet then errored on every enter/leave and the
// screen looked frozen. The URL alone still moved, which is why this asserts
// on RENDERED content and on the absence of page errors, not on the address.
//
// Needs a signed-in session: AUDIT_PW (docs/glass/audit/reset-audit-pw.sh) or
// HRMS_E2E_PW. Skips otherwise, loudly.
test.describe("KPI: Home -> KPI -> back, five times", () => {
	test.skip(!PW, "set AUDIT_PW or HRMS_E2E_PW to run this")

	test("returns within 2 s each time, renders both pages, throws nothing", async ({ browser }) => {
		const ctx = await browser.newContext({ storageState: await login(browser) })
		const page = await ctx.newPage()

		// The dev bundle boots from get_context_for_dev, which a site outside
		// developer_mode refuses. The production bundle never calls it, so the
		// stub is inert there.
		await page.route("**/hrms.www.hrms.get_context_for_dev", (route) =>
			route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({
					message: {
						site_name: "site",
						socketio_port: 9000,
						default_route: "/hrms",
						__messages: {},
					},
				}),
			})
		)

		await page.goto(`${BASE}/hrms/home`)
		await expect(page).toHaveURL(/\/hrms\/home/, { timeout: 15000 })
		// the sidebar item on desktop; a real tap, not a URL push
		const kpiNav = page.getByRole("button", { name: /^KPI$/i }).first()
		await expect(kpiNav).toBeVisible({ timeout: 15000 })

		// Armed only once Home is up: the raw dev index.html still carries the
		// Jinja `frappe.boot = {{ boot }}` line, a SyntaxError at document parse
		// that has nothing to do with the cycles under test.
		const errors = []
		page.on("pageerror", (e) => errors.push(e.message))

		for (let cycle = 1; cycle <= 5; cycle++) {
			await kpiNav.click()
			await expect(page).toHaveURL(/\/dashboard\/kpi/, { timeout: 2000 })
			// the page actually rendered: its header title, inside a mounted ion-page
			await expect(
				page.locator(".ion-page:not(.ion-page-hidden)").getByText(/^KPI$/).first(),
				`cycle ${cycle}: KPI page renders`
			).toBeVisible({ timeout: 2000 })

			await page.goBack()
			await expect(page, `cycle ${cycle}: back returns within 2 s`).toHaveURL(/\/hrms\/home/, {
				timeout: 2000,
			})
			await expect(
				page.getByRole("button", { name: /check in|check out/i }).first(),
				`cycle ${cycle}: Home renders again`
			).toBeVisible({ timeout: 2000 })
		}

		expect(errors, "no uncaught error during five cycles").toEqual([])
		await ctx.close()
	})
})

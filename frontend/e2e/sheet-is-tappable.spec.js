// A sheet's own contents must take taps (hotfix 23 Sep 2026): the scrim was
// teleported to <body> and painted over every sheet, so Check in / Check out,
// the day sheet and every other sheet could be seen but not used.
import { test, expect } from "@playwright/test"
import { BASE, login } from "./screens.mjs"

for (const [w, h] of [[390, 844], [1280, 800]]) {
	test(`the top element inside an open sheet is the sheet, at ${w}`, async ({ browser }) => {
		const ctx = await browser.newContext({ storageState: await login(browser), viewport: { width: w, height: h } })
		const page = await ctx.newPage()
		await page.goto(`${BASE}/hrms/more`)
		await page.getByText("Public holidays").filter({ visible: true }).first().click()
		await expect(page.locator("ion-modal.show-modal")).toHaveCount(1)
		await page.waitForTimeout(700)
		const inSheet = await page.evaluate(() => {
			const r = document.querySelector("ion-modal.show-modal").shadowRoot.querySelector(".modal-wrapper").getBoundingClientRect()
			return !!document.elementFromPoint(r.x + r.width / 2, r.y + 40)?.closest("ion-modal")
		})
		expect(inSheet).toBe(true)
	})
}

test("the day sheet's action button can be tapped", async ({ browser }) => {
	const ctx = await browser.newContext({ storageState: await login(browser), viewport: { width: 390, height: 844 } })
	const page = await ctx.newPage()
	await page.goto(`${BASE}/hrms/home`)
	await page.locator("ion-tab-button[id='tab-button-/dashboard/attendance']").click()
	await page.locator(".g-cal__day:not(.g-cal__day--empty)").nth(21).click()
	await expect(page.locator("ion-modal.show-modal")).toHaveCount(1)
	await page.waitForTimeout(700)
	const btn = page.locator("ion-modal.show-modal .g-btn, ion-modal.show-modal .g-list-row, ion-modal.show-modal button").first()
	await expect(btn).toBeVisible()
	await btn.click({ timeout: 3000 })
})

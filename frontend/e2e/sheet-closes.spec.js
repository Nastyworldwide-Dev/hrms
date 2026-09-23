// The sheet gate (alpha.4 plan): an open sheet blocks everything behind it,
// the dim area covers the whole shell and closes the sheet when tapped, and
// the sheet itself still takes taps — on phone and desktop. Rules: M3 bottom
// sheets (tapping the scrim dismisses), NN/g bottom sheets, WAI-ARIA dialog.
// Measured 23 Sep before the fix: the scrim sat inside the inert page, so a
// tap on it did nothing and the tab bar was never dimmed.
import { test, expect } from "@playwright/test"
import { BASE, login } from "./screens.mjs"

async function openHolidays(page) {
	await page.getByText("Public holidays").first().click()
	await expect(page.locator("ion-modal.show-modal")).toHaveCount(1)
	await page.waitForTimeout(700)
}

for (const [w, h] of [
	[390, 844],
	[1280, 800],
]) {
	test(`at ${w}: the scrim sits right under the sheet and covers the shell`, async ({ browser }) => {
		const ctx = await browser.newContext({ storageState: await login(browser), viewport: { width: w, height: h } })
		const page = await ctx.newPage()
		await page.goto(`${BASE}/hrms/more`)
		await openHolidays(page)
		const where = await page.evaluate(() => {
			const modal = document.querySelector("ion-modal.show-modal")
			const scrim = modal.previousElementSibling
			return {
				beforeSheet: scrim?.classList.contains("g-scrim"),
				inApp: scrim?.parentElement?.tagName,
				topLeft: document.elementFromPoint(10, 10)?.className,
			}
		})
		expect(where).toEqual({ beforeSheet: true, inApp: "ION-APP", topLeft: "g-scrim" })
	})

	test(`at ${w}: a tap on the dim area closes the sheet and leaves nothing behind`, async ({ browser }) => {
		const ctx = await browser.newContext({ storageState: await login(browser), viewport: { width: w, height: h } })
		const page = await ctx.newPage()
		await page.goto(`${BASE}/hrms/more`)
		await openHolidays(page)
		await page.mouse.click(w / 2, 20)
		await expect(page.locator("ion-modal.show-modal")).toHaveCount(0)
		await expect(page.locator(".g-scrim")).toHaveCount(0)
		await expect(page.locator(".ion-page[inert]")).toHaveCount(0)
		await expect(page).toHaveURL(/\/more/)
	})
}

test("at 390: the tab bar under an open sheet takes no tap", async ({ browser }) => {
	const ctx = await browser.newContext({ storageState: await login(browser), viewport: { width: 390, height: 844 } })
	const page = await ctx.newPage()
	await page.goto(`${BASE}/hrms/more`)
	await openHolidays(page)
	const tab = await page.evaluate(() => {
		const r = document.querySelector("ion-tab-bar").getBoundingClientRect()
		const hit = document.elementFromPoint(r.x + 30, r.y + r.height / 2)
		return !!hit?.closest("ion-tab-bar")
	})
	expect(tab).toBe(false)
})

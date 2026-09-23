// A sheet never outlives its page (audit P0-3, owner's report 23 Sep):
// Calendar -> tap a day -> Back left the day sheet floating over Home with
// its scrim stranded in the hidden Calendar page and the tab bar untappable.
import { test, expect } from "@playwright/test"
import { BASE, login } from "./screens.mjs"

test.use({ viewport: { width: 390, height: 844 } })

//: In-app navigation, as a person does it: a full page.goto would reload the
//: app and throw the sheet away, which is exactly the case that never broke.
async function openDaySheet(page) {
	await page.goto(`${BASE}/hrms/home`)
	await page.locator("ion-tab-button[id='tab-button-/dashboard/attendance']").click()
	await expect(page).toHaveURL(/dashboard\/attendance/)
	await page.locator(".g-cal__day:not(.g-cal__day--empty)").first().click()
	await expect(page.locator("ion-modal.g-modal.show-modal")).toHaveCount(1)
}

async function expectNoSheetLeft(page) {
	await expect(
		page.locator("ion-modal.g-modal.show-modal, ion-modal.g-modal:not(.overlay-hidden)")
	).toHaveCount(0)
	await expect(page.locator(".g-scrim")).toHaveCount(0)
	await expect(page.locator(".ion-page[inert]")).toHaveCount(0)
}

test("Back with the day sheet open leaves nothing behind, and the tab bar works", async ({
	browser,
}) => {
	const page = await (
		await browser.newContext({
			storageState: await login(browser),
			viewport: { width: 390, height: 844 },
		})
	).newPage()
	await openDaySheet(page)
	await page.goBack()
	await expectNoSheetLeft(page)
	// The tab bar is reachable: nothing of the sheet sits over it. (A toast
	// may, until F-6 stops raw errors toasting; it is not part of this bug.)
	const bar = await page.locator("ion-tab-bar").boundingBox()
	const onTop = await page.evaluate(
		([x, y]) => document.elementFromPoint(x, y)?.closest(".g-scrim, ion-modal") === null,
		[bar.x + bar.width / 2, bar.y + bar.height / 2]
	)
	expect(onTop).toBe(true)
	await page.locator("ion-tab-button[id='tab-button-/requests']").evaluate((el) => el.click())
	await expect(page).toHaveURL(/\/requests/)
	await expect(page).toHaveURL(/\/requests/)
})

test("Back pressed while the sheet is still opening leaves nothing behind", async ({
	browser,
}) => {
	const page = await (
		await browser.newContext({
			storageState: await login(browser),
			viewport: { width: 390, height: 844 },
		})
	).newPage()
	await page.goto(`${BASE}/hrms/home`)
	await page.locator("ion-tab-button[id='tab-button-/dashboard/attendance']").click()
	await expect(page).toHaveURL(/dashboard\/attendance/)
	await page.locator(".g-cal__day:not(.g-cal__day--empty)").first().click()
	await page.goBack()
	await page.waitForTimeout(800)
	await expectNoSheetLeft(page)
	// The page the sheet froze must be free when you come back to it.
	await page
		.locator("ion-tab-button[id='tab-button-/dashboard/attendance']")
		.evaluate((el) => el.click())
	await expect(page).toHaveURL(/dashboard\/attendance/)
	await page.waitForTimeout(400)
	expect(await page.locator(".ion-page[inert]").count()).toBe(0)
})

test("focus stays inside an open sheet", async ({ browser }) => {
	const page = await (
		await browser.newContext({
			storageState: await login(browser),
			viewport: { width: 390, height: 844 },
		})
	).newPage()
	await openDaySheet(page)
	for (let i = 0; i < 6; i++) await page.keyboard.press("Tab")
	const inside = await page.evaluate(() => !!document.activeElement?.closest("ion-modal"))
	expect(inside).toBe(true)
	await page.keyboard.press("Escape")
	await expectNoSheetLeft(page)
	// Focus comes back to the day that opened the sheet.
	const back = await page.evaluate(() => document.activeElement?.classList.contains("g-cal__day"))
	expect(back).toBe(true)
})

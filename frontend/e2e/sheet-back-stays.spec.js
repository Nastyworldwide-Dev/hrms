// Android Back with a sheet open closes ONLY the sheet (7 Oct 2026, alpha.41 S5).
//
// A sheet owns no history entry, so Back used to close it AND leave the page.
// The fix cannot cancel the popstate (@ionic/vue-router leaves its pending pop
// uncleared and the NEXT navigation animates as a back; traversalQueue.js), so
// router/sheetGuard.js redirects back onto the page being left. These asserts
// are on what is RENDERED, not on the URL alone, and the last one walks the
// stack to prove the browser history is the one the person had.
//
// Needs a signed-in session: AUDIT_PW or HRMS_E2E_PW. Skips otherwise.
import { test, expect } from "@playwright/test"
import { BASE, PW, login } from "./screens.mjs"

test.use({ viewport: { width: 390, height: 844 } })
test.skip(!PW, "set AUDIT_PW or HRMS_E2E_PW to run this")

/** What the tab outlet shows: the route, the URL, the top page and any page left invisible. */
const OUTLET_STATE = () => {
	const outlet = document.querySelector("ion-tabs ion-router-outlet")
	const pages = [...(outlet?.children || [])]
	const shown = pages.filter((p) => !p.classList.contains("ion-page-hidden"))
	const top = shown.sort((a, b) => Number(b.style.zIndex || 0) - Number(a.style.zIndex || 0))[0]
	const router = document.querySelector("#app").__vue_app__.config.globalProperties.$router
	return {
		route: router.currentRoute.value.path,
		url: location.pathname.replace(/^\/hrms/, ""),
		topHasCalendar: !!top?.querySelector(".g-cal"),
		topPath: top?.getAttribute("data-pageid") ?? null,
		invisible: pages.filter((p) => p.classList.contains("ion-page-invisible")).length,
		entries: history.length,
	}
}

async function settle(page) {
	await page.waitForFunction(
		() =>
			!document.querySelector(".ion-page-invisible") &&
			!document.getAnimations().some((a) => a.playState === "running"),
		null,
		{ timeout: 6000 }
	)
	await page.waitForTimeout(500)
}

async function openDaySheet(page) {
	await page.goto(`${BASE}/hrms/home`)
	await page.locator("ion-tab-button[id='tab-button-/dashboard/attendance']").click()
	await expect(page).toHaveURL(/dashboard\/attendance/)
	await settle(page)
	await page.locator(".g-cal__day:not(.g-cal__day--empty)").first().click()
	await expect(page.locator("ion-modal.g-modal.show-modal")).toHaveCount(1)
	await page.waitForTimeout(600)
}

async function newPage(browser) {
	const ctx = await browser.newContext({
		storageState: await login(browser),
		viewport: { width: 390, height: 844 },
	})
	return ctx.newPage()
}

test("Back with a sheet open closes the sheet and stays on the page", async ({ browser }) => {
	const page = await newPage(browser)
	await openDaySheet(page)
	const before = await page.evaluate(OUTLET_STATE)
	await page.goBack()
	await expect(page.locator("ion-modal.g-modal.show-modal")).toHaveCount(0)
	await settle(page)
	const after = await page.evaluate(OUTLET_STATE)
	expect(after.url).toBe("/dashboard/attendance")
	expect(after.route).toBe("/dashboard/attendance")
	expect(after.topHasCalendar, "the calendar is still the page on top").toBe(true)
	expect(after.invisible).toBe(0)
	// the stack is the one the person had: same number of entries
	expect(after.entries).toBe(before.entries)
	await expect(page.locator(".g-scrim")).toHaveCount(0)
	await expect(page.locator(".ion-page[inert]")).toHaveCount(0)
})

test("after that Back the next navigation renders, and Back then goes to the page before", async ({
	browser,
}) => {
	const page = await newPage(browser)
	await openDaySheet(page)
	await page.goBack()
	await expect(page.locator("ion-modal.g-modal.show-modal")).toHaveCount(0)
	await settle(page)

	// the next navigation must render as a forward navigation, not a back
	await page.locator("ion-tab-button[id='tab-button-/requests']").evaluate((el) => el.click())
	await expect(page).toHaveURL(/\/requests/)
	await settle(page)
	const next = await page.evaluate(OUTLET_STATE)
	expect(next.route).toBe("/requests")
	expect(next.url).toBe("/requests")
	expect(next.topHasCalendar, "the calendar must not stay painted over Requests").toBe(false)
	expect(next.invisible).toBe(0)

	// with no sheet open, Back is a plain Back again: Requests -> Calendar -> Home
	await page.goBack()
	await expect(page).toHaveURL(/dashboard\/attendance/)
	await settle(page)
	expect((await page.evaluate(OUTLET_STATE)).topHasCalendar).toBe(true)
	await page.goBack()
	await expect(page).toHaveURL(/\/home/)
	await settle(page)
	const home = await page.evaluate(OUTLET_STATE)
	expect(home.route).toBe("/home")
	expect(home.topHasCalendar).toBe(false)
	expect(home.invisible).toBe(0)
})

test("a sheet closed by a tab tap still lets the tab switch happen", async ({ browser }) => {
	const page = await newPage(browser)
	await openDaySheet(page)
	// the tab bar sits under the scrim; a script click is how a person's
	// swipe-dismiss then tap would land
	await page.locator("ion-tab-button[id='tab-button-/requests']").evaluate((el) => el.click())
	await expect(page).toHaveURL(/\/requests/)
	await expect(page.locator("ion-modal.g-modal.show-modal")).toHaveCount(0)
	await settle(page)
	expect((await page.evaluate(OUTLET_STATE)).topHasCalendar).toBe(false)
})

test("Back with a sheet open on a page that has a query string stays on that exact URL", async ({
	browser,
}) => {
	const page = await newPage(browser)
	// straight from Home, so Back leaves the PATH (a query-only step keeps the sheet)
	await page.goto(`${BASE}/hrms/home`)
	await settle(page)
	await page.evaluate(() =>
		document
			.querySelector("#app")
			.__vue_app__.config.globalProperties.$router.push("/dashboard/attendance?x=1")
	)
	await expect(page).toHaveURL(/x=1/)
	await settle(page)
	await page.locator(".g-cal__day:not(.g-cal__day--empty)").first().click()
	await expect(page.locator("ion-modal.g-modal.show-modal")).toHaveCount(1)
	await page.waitForTimeout(600)
	const before = await page.evaluate(OUTLET_STATE)
	await page.goBack()
	await expect(page.locator("ion-modal.g-modal.show-modal")).toHaveCount(0)
	await settle(page)
	await expect(page).toHaveURL(/dashboard\/attendance\?x=1$/)
	const after = await page.evaluate(OUTLET_STATE)
	expect(after.topHasCalendar).toBe(true)
	expect(after.invisible).toBe(0)
	expect(after.entries).toBe(before.entries)
	await page.locator("ion-tab-button[id='tab-button-/requests']").evaluate((el) => el.click())
	await expect(page).toHaveURL(/\/requests/)
	await settle(page)
	expect((await page.evaluate(OUTLET_STATE)).topHasCalendar).toBe(false)
})

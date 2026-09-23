// The right page transition per device (audit F-4): measured, not assumed.
// Before: the iOS push at 540 ms everywhere, and the desktop side nav slid on
// every section switch.
import { test, expect } from "@playwright/test"
import { BASE, login } from "./screens.mjs"

async function longestAnimation(page, action) {
	await page.evaluate(() => {
		window.__longest = 0
		const seen = new Set()
		const tick = () => {
			for (const a of document.getAnimations()) {
				if (seen.has(a)) continue
				// Page transitions only: a loading skeleton's pulse (the Requests
				// balances placeholder, 111402a6d) is not a navigation.
				const el = a.effect?.target
				if (el && !el.closest?.(".ion-page, ion-router-outlet")) continue
				if (el?.closest?.(".g-skeleton, [aria-hidden='true']")) continue
				seen.add(a)
				window.__longest = Math.max(window.__longest, a.effect?.getTiming?.().duration || 0)
			}
			if (performance.now() - start < 1500) requestAnimationFrame(tick)
		}
		const start = performance.now()
		requestAnimationFrame(tick)
	})
	await action()
	await page.waitForTimeout(1600)
	return page.evaluate(() => window.__longest)
}

test("desktop: a side-nav section switch does not animate", async ({ browser }) => {
	const ctx = await browser.newContext({ storageState: await login(browser), viewport: { width: 1280, height: 800 } })
	const page = await ctx.newPage()
	await page.goto(`${BASE}/hrms/home`)
	await page.waitForTimeout(1500)
	const ms = await longestAnimation(page, () => page.locator(".g-sidenav__item", { hasText: "Requests" }).first().click())
	expect(ms).toBeLessThanOrEqual(150)
	await ctx.close()
})

test("phone (not iOS): a pushed page fades in at most 200 ms", async ({ browser }) => {
	const ctx = await browser.newContext({ storageState: await login(browser), viewport: { width: 390, height: 844 } })
	const page = await ctx.newPage()
	await page.goto(`${BASE}/hrms/home`)
	await page.waitForTimeout(1500)
	const ms = await longestAnimation(page, () => page.locator("button[aria-label^='Notifications']").click())
	expect(ms).toBeGreaterThan(0)
	expect(ms).toBeLessThanOrEqual(200)
	await ctx.close()
})

test("a browser Back does not slide a second time", async ({ browser }) => {
	const ctx = await browser.newContext({ storageState: await login(browser), viewport: { width: 390, height: 844 } })
	const page = await ctx.newPage()
	await page.goto(`${BASE}/hrms/home`)
	await page.waitForTimeout(1500)
	await page.locator("button[aria-label^='Notifications']").click()
	await page.waitForTimeout(1200)
	const ms = await longestAnimation(page, () => page.goBack())
	expect(ms).toBe(0)
	await ctx.close()
})

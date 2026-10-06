// The list scroll gate (6 Oct 2026). "Load more on scroll" had the same naming defect as pull-to-refresh:
// ion-content's events reach the page as "ion-scroll" (Ionic's Vue wrapper renames them to kebab-case) while
// ListView listened for "ionScroll", so the handler never ran on the real app. This drives a real scroll and
// asserts the handler is reached: it asks the server for the next page when there is one, and (the test site's
// lists are short) at least asks the scroll element, which the debounced handler does first.
import { test, expect, devices } from "@playwright/test"
import { BASE, login } from "./screens.mjs"

test("a real scroll on a list reaches the list's scroll handler", async ({ browser }) => {
	const ctx = await browser.newContext({ ...devices["iPhone 13"], storageState: await login(browser) })
	const page = await ctx.newPage()
	await page.addInitScript(() => {
		window.__scrollHandlerCalls = 0
		const orig = HTMLElement.prototype.addEventListener
		HTMLElement.prototype.addEventListener = function (type, fn, opts) {
			if (this.tagName === "ION-CONTENT" && /^(ion-scroll|ionScroll)$/.test(type)) {
				const wrapped = (...a) => { window.__scrollHandlerCalls += 1; return fn(...a) }
				return orig.call(this, type, wrapped, opts)
			}
			return orig.call(this, type, fn, opts)
		}
	})
	await page.goto(`${BASE}/hrms/leave-applications`, { waitUntil: "domcontentloaded" })
	await page.waitForTimeout(3500)
	await page.evaluate(async () => {
		const c = document.querySelector("ion-content")
		const el = await c.getScrollElement()
		for (let i = 0; i < 10; i++) { el.scrollTop += 500; await new Promise((r) => setTimeout(r, 120)) }
	})
	await page.waitForTimeout(1500)
	const calls = await page.evaluate(() => window.__scrollHandlerCalls)
	expect(calls, "the list's scroll listener must receive the scroll").toBeGreaterThan(0)
})

// WCAG 1.4.10 reflow: at 320 CSS px with text at 200%, no page scrolls
// sideways (audit P0-13: Calendar and Requests did, and cut numbers in half).
import { test, expect } from "@playwright/test"
import { BASE, login } from "./screens.mjs"

for (const path of ["/home", "/dashboard/attendance", "/requests", "/dashboard/kpi", "/more"]) {
	test(`no sideways scroll at 320px / 200% text: ${path}`, async ({ browser }) => {
		const ctx = await browser.newContext({ storageState: await login(browser), viewport: { width: 320, height: 640 } })
		const page = await ctx.newPage()
		await page.goto(`${BASE}/hrms${path}`)
		await page.addStyleTag({ content: "html { font-size: 200% !important; }" })
		await page.waitForTimeout(1500)
		const wide = await page.evaluate(() => {
			const view = document.documentElement.clientWidth
			return [...document.querySelectorAll(".ion-page:not(.ion-page-hidden) *")]
				.filter((el) => {
					const r = el.getBoundingClientRect()
					return r.width > 0 && r.right > view + 1 && !el.closest(".g-toast, ion-toast, .overflow-x-auto, .hide-scrollbar, .g-lightfield")
				})
				.slice(0, 5)
				.map((el) => `${el.tagName.toLowerCase()}.${[...el.classList].join(".")} right=${Math.round(el.getBoundingClientRect().right)}`)
		})
		const scrolls = await page.evaluate(() => {
			const c = document.querySelector(".ion-page:not(.ion-page-hidden) ion-content")
			const inner = c?.shadowRoot?.querySelector(".inner-scroll")
			return inner ? inner.scrollWidth - inner.clientWidth : 0
		})
		expect({ wide, scrolls }).toEqual({ wide: [], scrolls: 0 })
		await ctx.close()
	})
}

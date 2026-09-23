import { expect, test } from "@playwright/test"

import { BASE, PW, login } from "./screens.mjs"

// BACK, then another navigation before the Back has landed (15 Sep 2026).
//
// Every navigation waits in main.js's guard for a network round trip
// (userResource.reload), so a Back stays IN FLIGHT for ~100-600 ms. A push or
// tap in that window cancelled the Back. vue-router accepts that; Ionic's
// router does not: @ionic/vue-router's afterEach returns early on the failure
// without clearing the pending "pop" it recorded, so the next navigation was
// animated as a back — the previous page stayed painted, the URL and route
// said /support, and the Helpdesk page never rendered until a reload.
//
// Asserts on RENDERED pages (which ion-page is shown on top in the tab outlet)
// against the route, never on the URL alone. 3 ways of going back x 6 delays
// x ITER runs; a fresh load per run so every run starts from the same state.
//
// Needs a signed-in session: AUDIT_PW or HRMS_E2E_PW. Skips otherwise.
const ITER = Number(process.env.BACK_RACE_ITER || 7)
const DELAYS = (process.env.BACK_RACE_DELAYS || "0,50,100,200,400,600").split(",").map(Number)
// The in-app back button went with 41dab817e (in alpha.3): a tab page has no
// Back, a section switch replaces history like a tab bar. The two browser
// Backs are what a person still has on a tab page.
const WAYS = ["router.back", "history.back"]
// The guard's userResource.reload round trip, as a phone sees it (100-600 ms).
// A local bench answers in ~15 ms, which closes the window and hides the race.
const LATENCY_MS = Number(process.env.BACK_RACE_LATENCY_MS ?? 300)

const DEV_CONTEXT = {
	status: 200,
	contentType: "application/json",
	body: JSON.stringify({
		message: { site_name: "site", socketio_port: 9000, default_route: "/hrms", __messages: {} },
	}),
}

/** What the tab outlet shows: the highest non-hidden page, and any page left invisible. */
const OUTLET_STATE = () => {
	const outlet = document.querySelector("ion-tabs ion-router-outlet")
	const title = (pg) =>
		(pg.querySelector("ion-header h1, ion-header")?.innerText || "").trim().split("\n")[0]
	const pages = [...(outlet?.children || [])]
	const shown = pages.filter((p) => !p.classList.contains("ion-page-hidden"))
	const top = shown.sort((a, b) => Number(b.style.zIndex || 0) - Number(a.style.zIndex || 0))[0]
	const router = document.querySelector("#app").__vue_app__.config.globalProperties.$router
	return {
		route: router.currentRoute.value.path,
		url: location.pathname.replace(/^\/hrms/, ""),
		top: top ? title(top) : null,
		invisible: pages.filter((p) => p.classList.contains("ion-page-invisible")).map(title),
	}
}

async function settle(page) {
	await page
		.waitForFunction(
			() => {
				if (document.querySelector(".ion-page-invisible")) return false
				// a page transition changes no class or z-index while it runs
				if (document.getAnimations().some((a) => a.playState === "running")) return false
				const key = [...document.querySelectorAll(".ion-page")]
					.map((p) => p.className + p.style.zIndex)
					.join("|")
				if (window.__raceKey !== key) {
					window.__raceKey = key
					window.__raceAt = Date.now()
					return false
				}
				return Date.now() - window.__raceAt > 400
			},
			null,
			{ timeout: 6000 }
		)
		.catch(() => {})
}

test.describe("BACK then navigate before the Back lands", () => {
	test.skip(!PW, "set AUDIT_PW or HRMS_E2E_PW to run this")
	test.setTimeout(ITER * DELAYS.length * WAYS.length * 15000)

	test("the page shown is always the page routed to", async ({ browser }) => {
		const ctx = await browser.newContext({ storageState: await login(browser) })
		const page = await ctx.newPage()
		await page.route("**/hrms.www.hrms.get_context_for_dev", (route) => route.fulfill(DEV_CONTEXT))
		await page.route("**/hrms.api.get_current_user_info", async (route) => {
			await new Promise((resolve) => setTimeout(resolve, LATENCY_MS))
			await route.continue().catch(() => {})
		})

		const stuck = []
		let runs = 0
		for (const way of WAYS) {
			for (const delay of DELAYS) {
				for (let i = 0; i < ITER; i++) {
					await page.goto(`${BASE}/hrms/home`)
					await page.waitForFunction(
						() => document.querySelector("#app")?.__vue_app__?.config?.globalProperties?.$router,
						null,
						{ timeout: 30000 }
					)
					await settle(page)
					await page.evaluate(() =>
						document
							.querySelector("#app")
							.__vue_app__.config.globalProperties.$router.push("/dashboard/kpi")
					)
					await expect(page).toHaveURL(/\/dashboard\/kpi/, { timeout: 10000 })
					await settle(page)

					await page.evaluate(
						async ({ way, delay }) => {
							const router =
								document.querySelector("#app").__vue_app__.config.globalProperties.$router
							if (way === "router.back") router.back()
							else if (way === "history.back") history.back()
							else {
								const outlet = document.querySelector("ion-tabs ion-router-outlet")
								const kpi = [...outlet.children].find(
									(p) => !p.classList.contains("ion-page-hidden") && p.style.zIndex !== "99"
								)
								;(kpi || document).querySelector('[aria-label="Back"]').click()
							}
							await new Promise((resolve) => setTimeout(resolve, delay))
							await router.push("/support")
						},
						{ way, delay }
					)
					await settle(page)
					const s = await page.evaluate(OUTLET_STATE)
					runs++
					// Titles as they are now: Helpdesk is "Help"; Home's header is the
					// Nadi mark ("n") with a hidden "Nadi" h1 (d83acb1b1).
					const expected = s.route.startsWith("/support")
						? /Help/
						: s.route === "/home"
						? /^n$|Nadi/
						: /Score/
					const ok =
						s.url === s.route && s.invisible.length === 0 && s.top !== null && expected.test(s.top)
					if (!ok) stuck.push({ way, delay, run: i, ...s })
				}
			}
		}
		const tally = {}
		for (const way of WAYS)
			for (const delay of DELAYS)
				tally[`${way} @${delay}ms`] = `${
					stuck.filter((s) => s.way === way && s.delay === delay).length
				}/${ITER}`
		console.info(
			`[back-race] ${stuck.length} stuck of ${runs} runs`,
			JSON.stringify(tally, null, 1)
		)
		console.info("[back-race] first stuck:", JSON.stringify(stuck.slice(0, 5)))
		expect(stuck, `${stuck.length} of ${runs} runs showed a page other than the route`).toEqual([])
		await ctx.close()
	})
})

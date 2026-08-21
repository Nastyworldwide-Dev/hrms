import { test, expect, chromium } from "@playwright/test"

import { BASE, login, screens, settle } from "./screens.mjs"

// Gate 6 — VISUAL REGRESSION. The layer that was missing.
//
// Every other gate reads source: tokens, contrast pairings, composition, surface
// counts. None of them can see a rendered pixel, which is how a build shipped
// with a login form that could not be clicked, list rows whose icon and label
// stacked on separate lines, and content permanently hidden behind the tab bar —
// all five gates green throughout.
//
// Baselines are the committed screenshots in docs/glass/audit/screens/ (see
// snapshotPathTemplate in playwright.config.js), so the images a finding cites
// and the images a regression is measured against are the same files.
//
// Re-baseline after an intended visual change:
//   npx playwright test --config=e2e/playwright.config.js e2e/visual.spec.js --update-snapshots
//
// The variant list mirrors docs/glass/audit/capture.mjs. Deliberately a subset
// of it: 390 in both themes catches essentially every layout regression, and
// 1440 dark catches the desktop column. Shooting all seven variants here would
// triple the runtime for very little extra signal.
const VARIANTS = [
	{ vp: { width: 390, height: 844 }, dsf: 2, theme: "dark", tag: "390-dark" },
	{ vp: { width: 390, height: 844 }, dsf: 2, theme: "light", tag: "390-light" },
	{ vp: { width: 1440, height: 900 }, dsf: 1, theme: "dark", tag: "1440-dark" },
]

test("visual: every screen matches its baseline", async () => {
	test.setTimeout(30 * 60 * 1000)

	const browser = await chromium.launch()
	const state = await login(browser)

	const probe = await browser.newContext({ storageState: state })
	const list = await screens(probe.request)
	await probe.close()

	const failures = []

	for (const v of VARIANTS) {
		for (const anon of [false, true]) {
			const batch = list.filter((s) => !!s.anon === anon)
			if (!batch.length) continue
			const ctx = await browser.newContext({
				viewport: v.vp,
				deviceScaleFactor: v.dsf,
				storageState: anon ? undefined : state,
				reducedMotion: "reduce",
			})
			await ctx.addInitScript((t) => {
				localStorage.setItem("hrms:theme", t)
				localStorage.setItem("hrms:reduce-transparency", "0")
			}, v.theme)
			const page = await ctx.newPage()

			for (const s of batch) {
				const name = `${s.slug}-${v.tag}.png`
				try {
					await page.goto(`${BASE}/hrms${s.path}`, { waitUntil: "networkidle", timeout: 35000 })
					await settle(page)
					await expect(page).toHaveScreenshot(name)
				} catch (e) {
					// Collect rather than throw, so one regression does not hide the
					// other forty. The gate prints the whole list and fails once.
					failures.push(`${name}: ${String(e.message || e).split("\n")[0].slice(0, 160)}`)
				}
			}
			await ctx.close()
		}
	}

	await browser.close()

	if (failures.length) {
		console.warn(`[visual] ${failures.length} screen(s) differ from baseline:`)
		for (const f of failures) console.warn(`[visual]   ${f}`)
	} else {
		console.info("[visual] all screens match their baselines")
	}
	expect(failures, `${failures.length} screen(s) differ from baseline`).toEqual([])
})

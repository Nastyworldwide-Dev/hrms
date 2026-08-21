import { test, chromium } from "@playwright/test"
import AxeBuilder from "@axe-core/playwright"
import { writeFileSync, mkdirSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

import { BASE, login, screens, settle } from "./screens.mjs"

const ROOT = dirname(dirname(dirname(fileURLToPath(import.meta.url))))
const REPORT = join(ROOT, "design", "gates", ".a11y-report.json")

// Glass gate 4 (spec §16.5.4). Every screen, both themes — not the single
// /hrms/login route this checked until 8.x, which was also the most broken
// screen in the app and still let the build pass.
//
// This spec only COLLECTS. design/gates/a11y.mjs diffs the report against
// design/a11y-baseline.json and decides pass/fail, so the accept/reject policy
// lives with the other gates rather than inside a Playwright assertion.
test("axe: every screen, both themes", async () => {
	test.setTimeout(15 * 60 * 1000)

	const browser = await chromium.launch()
	const state = await login(browser)

	const probe = await browser.newContext({ storageState: state })
	const list = await screens(probe.request)
	await probe.close()

	const report = {}
	for (const theme of ["dark", "light"]) {
		for (const anon of [false, true]) {
			const batch = list.filter((s) => !!s.anon === anon)
			if (!batch.length) continue
			const ctx = await browser.newContext({
				viewport: { width: 390, height: 844 },
				storageState: anon ? undefined : state,
				reducedMotion: "reduce",
			})
			await ctx.addInitScript((t) => {
				localStorage.setItem("hrms:theme", t)
				localStorage.setItem("hrms:reduce-transparency", "0")
			}, theme)
			const page = await ctx.newPage()

			for (const s of batch) {
				const key = `${s.slug}:${theme}`
				try {
					await page.goto(`${BASE}/hrms${s.path}`, { waitUntil: "networkidle", timeout: 35000 })
					await settle(page)
					const results = await new AxeBuilder({ page }).analyze()
					const counts = {}
					for (const v of results.violations) {
						// impact is what the gate enforces on; keep it with the count
						counts[v.id] = { impact: v.impact, nodes: v.nodes.length }
					}
					report[key] = counts
					const serious = results.violations.filter((v) =>
						["serious", "critical"].includes(v.impact)
					)
					console.info(
						`[a11y] ${key}: ${results.violations.length} violations ` +
							`(${serious.length} serious/critical), ${results.passes.length} passes`
					)
					for (const v of results.violations) {
						console.warn(`[a11y]   ${v.impact}: ${v.id} — ${v.help} (${v.nodes.length} nodes)`)
					}
				} catch (e) {
					report[key] = { __error: { impact: "critical", nodes: 1 } }
					console.warn(`[a11y] ${key}: FAILED TO RENDER — ${String(e).split("\n")[0].slice(0, 120)}`)
				}
			}
			await ctx.close()
		}
	}

	await browser.close()
	mkdirSync(dirname(REPORT), { recursive: true })
	writeFileSync(REPORT, JSON.stringify(report, null, 2))
	console.info(`[a11y] wrote ${Object.keys(report).length} screen-theme results`)
})

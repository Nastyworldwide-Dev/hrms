import { test } from "@playwright/test"
import AxeBuilder from "@axe-core/playwright"

// Glass gate 4 smoke (spec §16.5.4) — proves the axe harness runs end to end.
// Login is the one route that renders without a session. Phase 4/5 extend this
// to every screen in both themes; until then violations are logged, not failed.
test("axe smoke: login screen", async ({ page }) => {
	await page.goto("/hrms/login")
	await page.waitForLoadState("networkidle")

	const results = await new AxeBuilder({ page }).analyze()
	console.info("[a11y] axe on /hrms/login:", {
		violations: results.violations.length,
		passes: results.passes.length,
	})
	for (const v of results.violations) {
		console.warn(`[a11y] ${v.impact}: ${v.id} — ${v.help} (${v.nodes.length} nodes)`)
	}
	// report-only: no expect() on violations until phase 4 flips enforcement
})

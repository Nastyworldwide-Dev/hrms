// Role–token binding, as a unit assertion.
//
// `accent.DEFAULT` resolved to --accent-ink while `accent-100` resolved to
// --brand, so `bg-accent` painted #3F5C00 dark olive and the name meant the
// opposite of what it said. Eight form submits wrote `!bg-accent` expecting
// chartreuse and got olive.
//
// It survived a 148-finding audit because **--accent-ink EQUALS --brand in dark
// theme**. The two tokens collapse to one value there, so the wrong one renders
// correctly in the only theme anyone screenshotted. That is the failure mode
// this file exists to prevent: a token pair that is distinct in one theme and
// identical in another hides a defect in whichever theme collapses it.
//
// The config imports frappe-ui's preset by an extensionless path that neither
// plain node nor mock.module can resolve, so the config half is asserted on
// source text — the same approach as resource-config-first.test.mjs. The token
// half reads the GENERATED values, which is where the real signal is.
//
// Run with: node --test "frontend/**/*.test.js"
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const config = read("./tailwind.config.js")
const tokenCss = read("./src/theme/glass.css")

/** The accent block, so a match cannot stray into the ink ramp above it. */
const accentBlock = config.slice(config.indexOf("accent: {"), config.indexOf("ground:"))

/**
 * A generated token's value, per theme.
 *
 * glass.css emits :root (light) and then a dark override block that ONLY
 * redeclares the tokens that change. A theme-constant token like --g-brand
 * appears once and is inherited, so reading the dark block alone returns null
 * for it — which is a missing value, not a different one. Fall back to :root.
 */
function token(name, theme) {
	const blocks = tokenCss.split(/\[data-theme=["']?dark/)
	const light = blocks[0]
	const dark = blocks[1] || ""
	const find = (src) => {
		const m = src.match(new RegExp(`--g-${name}:\\s*([^;]+);`))
		return m ? m[1].trim() : null
	}
	return theme === "dark" ? find(dark) ?? find(light) : find(light)
}

test("accent.DEFAULT is the BRAND fill, not the ink", () => {
	const m = accentBlock.match(/DEFAULT:\s*"rgb\(var\(--g-([a-z-]+)-rgb\)/)
	assert.ok(m, "accent.DEFAULT must be declared")
	assert.equal(
		m[1],
		"brand",
		"bg-accent must paint the brand — pointing DEFAULT at accent-ink is how eight form submits went dark olive"
	)
})

test("the ink steps stay ink — §2.4 forbids brand setting type on light", () => {
	for (const step of [500, 600, 700, 800, 900]) {
		assert.match(
			accentBlock,
			new RegExp(`${step}:\\s*"rgb\\(var\\(--g-accent-ink-rgb\\)`),
			`accent-${step} must remain the ink`
		)
	}
})

test("brand and accent-ink are DISTINCT in light theme", () => {
	const brand = token("brand", "light")
	const ink = token("accent-ink", "light")
	assert.ok(brand && ink, "both tokens must be emitted")
	assert.notEqual(brand, ink, "if these collapsed in light too, no theme could reveal a swap")
})

test("brand and accent-ink COLLAPSE in dark — the masking this file guards", () => {
	// Not a defect: §2.4 wants accent type to be the brand on dark. But it means
	// dark theme cannot reveal a brand/ink mix-up, so any check that runs only in
	// dark is blind to one. Pinned so the assumption is explicit rather than
	// rediscovered by a human on a light-themed deployment.
	const brand = token("brand", "dark")
	const ink = token("accent-ink", "dark")
	assert.equal(
		brand,
		ink,
		"if these ever differ in dark, the light-only blind spot is gone and this test can be retired"
	)
})

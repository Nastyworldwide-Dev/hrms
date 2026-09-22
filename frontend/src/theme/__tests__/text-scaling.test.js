// Type responds to the reader's text size (revamp §24, WCAG 2.1 SC 1.4.4).
//
// The ramp is AUTHORED in px — that is how a type scale is reasoned about and
// reviewed, and how the 1.2 ratio was checked — and EMITTED in rem, because a
// px font-size ignores the browser's or OS's text setting completely. Somebody
// who has turned their phone's text up got the same 12px caption as everybody
// else, which is the failure 1.4.4 describes: text that cannot reach 200%.
//
// SPACING deliberately stays in px. A layout that grows with text size reflows
// unpredictably, and the 320px floor (§27) is measured in CSS px, so tying the
// two together would make the narrow case untestable.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")
const tokens = JSON.parse(readFileSync(join(SRC, "../../design/tokens.json"), "utf8"))
const css = read("theme/glass.css")

test("every type size is emitted in rem", () => {
	const px = [...css.matchAll(/--g-type-([a-z-]+)-size:\s*([^;]+);/g)].filter(
		(m) => !m[2].trim().endsWith("rem")
	)
	assert.deepEqual(
		px.map((m) => `${m[1]} = ${m[2].trim()}`),
		[],
		"a px font-size does not respond to the reader's text setting"
	)
})

test("the rem values are the px ramp, converted — not a second ramp", () => {
	// The token file stays in px so the scale can be reviewed as one. If these
	// ever disagree, somebody has edited the generated CSS by hand.
	for (const [name, step] of Object.entries(tokens.type.scale)) {
		const authored = Number.parseFloat(step.size)
		const emitted = css.match(new RegExp(`--g-type-${name}-size:\\s*([\\d.]+)rem`))
		assert.ok(emitted, `${name} is emitted`)
		assert.equal(
			Number(emitted[1]) * 16,
			authored,
			`${name}: ${emitted[1]}rem is not ${authored}px at a 16px root`
		)
	}
})

test("spacing stays in px", () => {
	// Growing the layout with the text is a different feature with a different
	// failure mode, and it would make the 320px reflow floor unmeasurable.
	const remSpacing = [
		...css.matchAll(/--g-(screen-gutter|stack-[a-z]+|pad-[a-z]+):\s*([^;]+);/g),
	].filter((m) => m[2].includes("rem"))
	assert.deepEqual(
		remSpacing.map((m) => m[1]),
		[],
		"spacing is CSS px by design"
	)
})

test("the iOS zoom rule is still a literal", () => {
	// 16px there is a PLATFORM constant — the threshold below which Safari
	// zooms a focused field — not a step on our scale. Converting it to rem
	// would make it move with the reader's setting and the zoom would return.
	const components = read("theme/glass-components.css")
	const rule = components.slice(components.indexOf("iOS Safari zooms"))
	assert.match(rule, /font-size:\s*16px/, "the input floor stays in px")
})

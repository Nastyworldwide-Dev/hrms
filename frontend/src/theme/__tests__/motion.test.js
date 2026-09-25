// Motion is a preference the app must obey, and a scale it must read from
// (revamp slice A8, WCAG 2.3.3).
//
// Two findings, both from measurement rather than review:
//
//   prefers-reduced-motion was honoured in FOUR components out of about
//   ninety. Vestibular disorders are why that media query exists — unasked-for
//   motion can cause nausea and dizziness — so honouring it in four places is
//   the same as not honouring it.
//
//   `--motion-glide` was referenced four times in SopFormSheet and defined
//   nowhere since the Modernist stylesheet was deleted. An undefined custom
//   property makes the whole declaration invalid, and CSS drops invalid
//   declarations silently, so those transitions were not slow or wrong — they
//   did not exist. The same shape hid three more: the check-in sheet's
//   location title and detail (a `font:` shorthand naming a variable the
//   builder never emits, so they rendered at inherited size) and the update
//   prompt's drop shadow.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")
const tokens = JSON.parse(readFileSync(join(SRC, "../../design/tokens.json"), "utf8"))

const decomment = (text) =>
	text
		.split(/(\/\*[\s\S]*?\*\/)/)
		.filter((part) => !part.startsWith("/*"))
		.join("")

const components = decomment(read("theme/glass-components.css"))
const reduced = () =>
	components.slice(components.lastIndexOf("@media (prefers-reduced-motion: reduce)"))

test("reduced motion is honoured for everything, not for four components", () => {
	assert.match(
		components,
		/@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{\s*\*,\s*\*::before,\s*\*::after/,
		"one block, every element"
	)
})

test("reduced motion uses 1ms, not 0", () => {
	// `transition: none` / 0ms cancels a transition mid-flight, so Vue's
	// <Transition> never hears transitionend and can strand an element in its
	// enter-from state: invisible, still taking up layout. 1ms completes, fires
	// the event, and nobody perceives it.
	assert.match(reduced(), /transition-duration:\s*1ms\s*!important/)
	assert.match(reduced(), /animation-duration:\s*1ms\s*!important/)
	assert.doesNotMatch(reduced(), /transition-duration:\s*0m?s/, "0 strands a Vue transition")
})

test("smooth scrolling is motion too", () => {
	assert.match(reduced(), /scroll-behavior:\s*auto\s*!important/)
})

test("no component references a motion variable that does not exist", () => {
	// The failure is silent by design of CSS itself, which is why it needs a
	// test rather than an eye.
	const theme = ["glass.css", "glass.variables.css", "glass-components.css"]
		.map((f) => read(`theme/${f}`))
		.join("\n")
	const defined = new Set([...theme.matchAll(/^\s*(--[a-z0-9-]+):/gm)].map((m) => m[1]))
	const sheet = decomment(read("views/sop/SopFormSheet.vue"))
	const used = [...sheet.matchAll(/var\(\s*(--[a-z0-9-]+)\s*\)/g)].map((m) => m[1])
	// Since alpha.10 the sheet is built from kit components, which carry their
	// own motion; any variable it still names must resolve.
	assert.deepEqual(
		used.filter((name) => name.startsWith("--g-") && !defined.has(name)),
		[],
		"every --g- reference resolves"
	)
	assert.deepEqual(
		used.filter((name) => name === "--motion-glide"),
		[],
		"--motion-glide belonged to a stylesheet that no longer exists"
	)
})

test("the state-change step sits in Material's short band", () => {
	// 50-200ms. Long enough to read as a change rather than a jump, short
	// enough that somebody tapping quickly never waits for it.
	const ms = parseInt(tokens.motion["state-change"].duration, 10)
	assert.ok(ms >= 50 && ms <= 200, `state-change is ${ms}ms; Material's short band is 50-200`)
})

test("the check-in sheet's location lines have a size again", () => {
	// A `font:` shorthand naming --g-type-card-title, which the builder never
	// emits — it writes one variable per facet. The declaration was invalid and
	// dropped, so these rendered at whatever they inherited.
	const panel = decomment(read("components/CheckInPanel.vue"))
	assert.doesNotMatch(panel, /font:\s*var\(--g-type-[a-z-]+\)/, "no facet-less shorthand")
	assert.match(panel, /font-size:\s*var\(--g-type-card-title-size\)/, "the title has a size")
	assert.match(panel, /color:\s*var\(--g-ink2\)/, "and the detail has its colour back")
})

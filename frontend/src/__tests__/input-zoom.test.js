// A tapped field never zooms the page (spec §19 DECISION 3).
//
// iOS Safari zooms the whole viewport when a text field is focused whose
// computed font-size is under 16px, and it does not cleanly zoom back. The
// employee is left on a magnified page, panning sideways to reach the submit
// button — on every form in the app.
//
// ALREADY FIXED, and this file exists because nothing said so. The rule is in
// glass-components.css and has been for some time; the spec still lists
// DECISION 3 as open, and a pre-2.0 audit (22 Sep 2026) re-derived the defect
// from `.g-input`'s 12.5px `--g-type-row-label-size` and began fixing it a
// second time. The rule was two thousand lines further down, winning on
// source order, doing the job. A fix nobody can find is a fix somebody will
// pay for again — so it is pinned here, and the spec now records the decision
// as taken.
//
// What is pinned is the BEHAVIOUR, not the current spelling: text entry is at
// least 16px, and the rest of the app was not resized to achieve it.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const css = readFileSync(
	fileURLToPath(new URL("../theme/glass-components.css", import.meta.url)),
	"utf8"
)
const tokens = JSON.parse(
	readFileSync(fileURLToPath(new URL("../../../design/tokens.json", import.meta.url)), "utf8")
)

// Every selector that styles text entry, with the declarations that follow it.
function declarationsFor(selector) {
	const out = []
	for (const m of css.matchAll(
		new RegExp(`(^|,|\\n)\\s*${selector.replace(/[.[\]"]/g, "\\$&")}[^{]*\\{([^}]*)\\}`, "g")
	)) {
		out.push(m[2])
	}
	return out
}

test("text entry is at least 16px, so focusing a field cannot zoom the page", () => {
	// The LAST font-size to apply wins, and these rules sit below every other
	// input rule on purpose — so read the last one, not the first.
	for (const selector of [".g-input", ".g-search__input"]) {
		const sizes = declarationsFor(selector)
			.map((body) => body.match(/font-size:\s*([^;]+);/))
			.filter(Boolean)
			.map((m) => m[1].trim())
		assert.ok(sizes.length, `${selector} should set a font-size somewhere`)
		const winning = sizes[sizes.length - 1]
		const px = winning.startsWith("var(")
			? parseFloat(tokens.type.scale[winning.match(/--g-type-([a-z-]+)-size/)[1]].size)
			: parseFloat(winning)
		assert.ok(px >= 16, `${selector} ends up at ${px}px; iOS zooms under 16`)
	}
})

test("the zoom rule says why it is a literal and not a token", () => {
	// 16 is a platform constant, not a design decision — a type-scale token
	// would invite a designer to tune it and silently bring the zoom back.
	const i = css.indexOf("iOS Safari zooms")
	assert.ok(i > 0, "the rule carries its reason")
	const comment = css.slice(i, css.indexOf("*/", i))
	assert.match(
		comment,
		/16px is the iOS threshold|platform constant/,
		"and says 16 is not ours to choose"
	)
	assert.match(
		comment,
		/specificity|after every input rule/,
		"and why its position in the file matters"
	)
})

test("the fix did not resize the rest of the app", () => {
	// `row-label` is a LIST ROW's label — "Apply for leave" — shared by a dozen
	// surfaces that are not inputs. The zoom fix must never have been the thing
	// that set its size: raising every row to 16 to stop a keyboard zooming is a
	// redesign wearing a bugfix's clothes.
	//
	// It was pinned at 12.5px when this test was written. The 22 Sep modular
	// ramp moved it to 14px — the body-copy floor — as a TYPE decision taken on
	// the ramp, not as a side effect of the input rule. So what is asserted is
	// the invariant that actually protects the app: row-label stays BELOW the
	// 16px input size, so `.g-input` still has to override it for itself, and
	// the two cannot be collapsed into one value by a later edit.
	const rowLabel = parseFloat(tokens.type.scale["row-label"].size)
	assert.ok(
		rowLabel < 16,
		`row-label is ${rowLabel}px; at 16 the input rule would be indistinguishable from the row rule`
	)
	// And it is still real body copy, not a caption: the ramp's floor for
	// anything a sentence is set in.
	assert.ok(rowLabel >= 14, `row-label is ${rowLabel}px; body copy floor is 14px`)
})

test("zoom is off (owner ruling, 25 Sep 2026)", () => {
	// SUPERSEDED: the owner turned zoom off ("turn off zoom"), for a native
	// feel. iOS Safari ignores user-scalable=no since iOS 10, so three layers:
	// the viewport meta (Android, older iOS), Safari's own gesture events
	// cancelled (pinch), and touch-action: manipulation (double-tap). Text
	// size still follows the phone's own setting, so reading help stays.
	const html = readFileSync(fileURLToPath(new URL("../../index.html", import.meta.url)), "utf8")
	const viewport = html.match(/<meta[^>]*name="viewport"[^>]*>/)
	assert.ok(viewport, "there is a viewport meta")
	assert.match(viewport[0], /maximum-scale=1/)
	assert.match(viewport[0], /user-scalable=no/)
	const main = readFileSync(fileURLToPath(new URL("../main.js", import.meta.url)), "utf8")
	assert.match(main, /blockZoom\(\)/)
	const guard = readFileSync(fileURLToPath(new URL("../utils/blockZoom.js", import.meta.url)), "utf8")
	for (const ev of ["gesturestart", "gesturechange"]) assert.match(guard, new RegExp(ev))
	assert.match(guard, /touches\.length > 1/)
})

test("the type floor holds (spec DECISION 5)", () => {
	// The mockup drew 7.5 and 8.5px type; §14.4 exception 6 raised the floor to
	// 10. Checked here rather than assumed: the audit that produced this file
	// expected to find violations and found none, which is worth keeping true.
	const under = Object.entries(tokens.type.scale)
		.filter(([, v]) => v.size && parseFloat(v.size) < 10)
		.map(([k, v]) => `${k}=${v.size}`)
	assert.deepEqual(under, [], "10px is the floor (§4.2, §14.4 exception 6)")
})

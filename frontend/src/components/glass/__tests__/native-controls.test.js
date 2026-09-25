// GSelect / GCheckbox / GSwitch are the native form controls that replaced
// frappe-ui's grey kit. The node runner does not compile SFCs, so the
// accessibility contract is pinned on the source (like GBanner.test.js), and
// the 0/1-vs-boolean rule is pinned on the shared pure helper.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { toggleValue } from "../../../utils/toggleValue.js"

const read = (rel) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8")
const css = read("../../../theme/glass-components.css")

// the rule body of `selector { ... }` in the theme
function rule(selector) {
	const start = css.indexOf(`\n${selector} {`)
	assert.notEqual(start, -1, `theme must style ${selector}`)
	return css.slice(start, css.indexOf("}", start))
}

test("GSelect is a native <select> in the input skin with a visible focus ring", () => {
	const src = read("../GSelect.vue")
	assert.match(src, /<select[\s\S]*class="g-input g-select__native g-focusable"/)
	assert.match(src, /value="">\{\{ placeholder \}\}<\/option>/, "empty first option")
	assert.match(src, /\$emit\('update:modelValue', \$event\.target\.value\)/)
	assert.doesNotMatch(src, /frappe-ui/)
	// .g-input carries min-height 44px
	assert.match(rule(".g-input"), /min-height: 44px/)
})

test("GCheckbox is a native checkbox whose labelled row is the 44px target", () => {
	const src = read("../GCheckbox.vue")
	assert.match(src, /<label class="g-check"/, "the label row wraps the box — the whole row taps")
	assert.match(src, /type="checkbox"/)
	assert.match(src, /class="g-check__box g-focusable"/)
	assert.match(src, /toggleValue\(props\.modelValue/)
	assert.match(rule(".g-check"), /min-height: var\(--g-touch-target-min\)/)
})

test("GSwitch is a native switch input in a 44px label (alpha.7 B17)", () => {
	// Safari 17.4+ draws Apple's own switch, announces it as a switch and, on
	// iOS 18, gives the only haptic a web app gets (webkit.org/blog/15865).
	const src = read("../GSwitch.vue")
	assert.match(src, /<input\s+type="checkbox"\s+switch/)
	assert.match(src, /role="switch"/)
	assert.match(src, /:checked="on"/)
	assert.match(src, /<label\s+class="g-switch"/)
	assert.match(src, /'g-switch--drawn': !NATIVE_SWITCH/)
	assert.match(src, /toggleValue\(props\.modelValue/)
	const r = rule(".g-switch")
	assert.match(r, /min-height: var\(--g-touch-target-min\)/)
	assert.match(r, /min-width: var\(--g-touch-target-min\)/)
})

test("toggle answers in the type it was given (0/1 stays 0/1, boolean stays boolean)", () => {
	assert.equal(toggleValue(0, true), 1)
	assert.equal(toggleValue(1, false), 0)
	assert.equal(toggleValue(false, true), true)
	assert.equal(toggleValue(true, false), false)
	// unset field (undefined/null) is the app's boolean default
	assert.equal(toggleValue(undefined, true), true)
})

test("date pickers are native inputs with Frappe's formats", () => {
	const d = read("../GDatePicker.vue")
	assert.match(d, /type="date"/)
	assert.match(d, /:min="minDate \|\| undefined"/)
	const dt = read("../GDateTimePicker.vue")
	assert.match(dt, /type="datetime-local"/)
	assert.match(dt, /fromDatetimeLocal\(\$event\.target\.value\)/)
	assert.match(dt, /:value="toDatetimeLocal\(modelValue\)"/)
})

test("Link opens a Glass sheet of 44px rows, not frappe-ui's Autocomplete", () => {
	const src = read("../../Link.vue")
	assert.match(src, /<GModal[\s\S]*:is-open="open"/)
	assert.match(src, /role="listbox"/)
	assert.match(src, /role="option"[\s\S]*class="g-row g-row--tappable/)
	assert.match(src, /frappe\.desk\.search\.search_link/, "data fetching unchanged")
	assert.doesNotMatch(src, /<Autocomplete|import[^\n]*Autocomplete/)
})

// alpha.7 0.7: Appearance always has a value, yet iOS drew the empty option
// as a blank first slot above "Light". The empty option exists only when it
// says something (a placeholder such as "All") or nothing is chosen yet.
test("GSelect draws the empty option only when it means something", () => {
	const src = read("../GSelect.vue")
	assert.match(
		src,
		/<option v-if="placeholder \|\| modelValue === '' \|\| modelValue == null" value="">\{\{ placeholder \}\}<\/option>/
	)
})

// alpha.8 (owner's iPhone, iOS 26: "Notifications" and "Shift reminders"
// drawn as blue checkboxes). frappe-ui's Tailwind forms plugin sets
// `[type=checkbox] { appearance: none }` and paints a blue tick, which strips
// Safari's own switch. The switch input gets its native appearance back.
test("the native switch keeps Safari's own look", () => {
	const r = rule(".g-switch__input")
	assert.match(r, /appearance: auto/)
	assert.match(r, /-webkit-appearance: auto/)
	assert.match(r, /background: none/)
})

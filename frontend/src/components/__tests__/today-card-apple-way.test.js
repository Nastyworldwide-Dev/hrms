// alpha.12, the owner's "Apple way" Today card (mockups/mockup-nadi-apple-way.html):
// every movement is one of Apple's own symbol effects, once, for a reason, and
// all of it stops under Reduce Motion (Apple, motion: "Add motion purposefully").
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const bar = read("../NowBar.vue")
const css = read("../../theme/glass-components.css")

test("while working, a gauge runs from the shift start to its end, labelled at both ends", () => {
	assert.match(bar, /shiftGauge\(/)
	assert.match(bar, /class="g-now__gauge"/)
	assert.match(bar, /role="meter"|role="progressbar"/)
	assert.match(bar, /:aria-valuenow=/)
	assert.match(bar, /clockTime\(shift\.start\)[\s\S]*clockTime\(shift\.end\)/)
})

test("past the end the gauge turns orange; long past it asks 'Forgot to check out?'", () => {
	assert.match(bar, /g-now--past/)
	assert.match(bar, /Forgot to check out\?/)
	assert.match(css, /\.g-now--past \.g-now__gauge-fill\s*\{[^}]*var\(--g-warn\)/)
})

test("the working dot breathes (Apple Breathe), from the motion scale", () => {
	assert.match(css, /\.g-now--working \.g-now__dot\s*\{[^}]*animation:\s*g-breathe var\(--g-motion-breathe-duration\)/)
	assert.match(css, /@keyframes g-breathe/)
})

test("the running time rolls when a minute passes (content replace), not snaps", () => {
	assert.match(bar, /<Transition name="g-roll"/)
	assert.match(css, /\.g-roll-enter-active[^{]*\{[^}]*var\(--g-motion-symbol-duration\)/)
})

test("the gauge fill moves on the progress scale", () => {
	assert.match(css, /\.g-now__gauge-fill\s*\{[^}]*transition:\s*width var\(--g-motion-progress-duration\)/)
})

// A saved punch is confirmed on the card's own button: a tick draws itself
// (Apple: Draw On), once, then the button settles on its next action.
const panel = read("../CheckInPanel.vue")
test("a saved punch draws a tick on the Today button, once", () => {
	assert.match(panel, /justSaved\.value = true/)
	assert.match(panel, /class="g-btn__tick"/)
	assert.match(css, /\.g-btn__tick path\s*\{[^}]*stroke-dashoffset/)
	assert.match(css, /animation:\s*g-draw var\(--g-motion-symbol-duration\)/)
})

// Measured live 26 Sep 2026: "9h 44m left" at 13:46 on a 09:00-18:00 shift —
// the gauge read the DEVICE clock. It reads the employee's wall clock from the
// server (`time`, employee_now), advanced by the time since the answer.
test("the gauge's 'now' is the employee's wall clock from the server, not the device's", () => {
	assert.match(bar, /data\.value\.time/)
	assert.doesNotMatch(bar, /siteTime\(new Date\(\)\.toISOString\(\)\)/)
})

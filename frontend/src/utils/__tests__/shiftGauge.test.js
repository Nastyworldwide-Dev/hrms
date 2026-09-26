// alpha.12 Apple-way card (owner, 26 Sep 2026): a capacity gauge from the
// shift's start to its end (Apple, gauges: "label the current value and both
// endpoints"; "change the fill colour when the value reaches significant
// levels"). Worked out from the clock and the shift window, never counted up.
import { test } from "node:test"
import assert from "node:assert/strict"
import { shiftGauge, FORGOT_AFTER_MIN } from "../shiftGauge.js"

const at = (hhmm) => {
	const [h, m] = hhmm.split(":").map(Number)
	return h * 60 + m
}

test("mid-shift: the share done and the time left", () => {
	const g = shiftGauge({ start: "09:00", end: "18:00", nowMin: at("12:20") })
	assert.equal(g.fraction, 200 / 540)
	assert.equal(g.leftMin, 340)
	assert.equal(g.pastMin, 0)
	assert.equal(g.level, "working")
})

test("before the shift starts the gauge is empty, not negative", () => {
	const g = shiftGauge({ start: "09:00", end: "18:00", nowMin: at("08:10") })
	assert.equal(g.fraction, 0)
	assert.equal(g.level, "working")
})

test("past the end: full, orange, minutes past", () => {
	const g = shiftGauge({ start: "09:00", end: "18:00", nowMin: at("18:40") })
	assert.equal(g.fraction, 1)
	assert.equal(g.pastMin, 40)
	assert.equal(g.level, "past")
})

test("long past the end: 'forgot to check out?'", () => {
	assert.equal(shiftGauge({ start: "09:00", end: "18:00", nowMin: at("18:00") + FORGOT_AFTER_MIN }).level, "forgot")
	assert.equal(shiftGauge({ start: "09:00", end: "18:00", nowMin: at("18:00") + FORGOT_AFTER_MIN - 1 }).level, "past")
})

test("a night shift crosses midnight: 22:00-06:00 at 02:00 is half done", () => {
	const g = shiftGauge({ start: "22:00", end: "06:00", nowMin: at("02:00") })
	assert.equal(g.fraction, 0.5)
	assert.equal(g.leftMin, 240)
})

test("no shift window: no gauge", () => {
	assert.equal(shiftGauge({ start: "", end: "18:00", nowMin: 600 }), null)
})

// One session rule, the server's (remote_checkin.session_open_until): open
// until 06:00 the morning after the check-in, or the shift's check-out window
// if later. The button used a 16-hour cap and offered "Check in" at 01:00-03:00
// to people still working (employee report, 25 Sep 2026; reproduced in WebKit).
import { test } from "node:test"
import assert from "node:assert/strict"
import dayjs from "dayjs"
import utc from "dayjs/plugin/utc.js"
import timezone from "dayjs/plugin/timezone.js"

dayjs.extend(utc)
dayjs.extend(timezone)
globalThis.dayjs = dayjs
globalThis.window = { frappe: { boot: { sysdefaults: { time_zone: "Asia/Kuala_Lumpur" } } } }

const { sessionOpenUntil, sessionIsOpen } = await import("../checkinSession.js")
const at = (s) => dayjs.tz(s, "Asia/Kuala_Lumpur").valueOf()

test("a day shift is open until 06:00 the next morning", () => {
	assert.equal(sessionOpenUntil("2026-09-24 09:00:00", "2026-09-24 19:00:00"), at("2026-09-25 06:00:00"))
})

test("a night shift's own check-out window wins when later", () => {
	assert.equal(sessionOpenUntil("2026-09-24 22:00:00", "2026-09-25 07:00:00"), at("2026-09-25 07:00:00"))
})

test("the reported cases: still Check out at midnight and at 3 am", () => {
	for (const [inAt, now] of [
		["2026-09-24 08:00:00", "2026-09-25 00:01:00"],
		["2026-09-24 09:00:00", "2026-09-25 01:01:00"],
		["2026-09-24 11:00:00", "2026-09-25 03:00:00"],
	]) {
		assert.equal(sessionIsOpen({ time: inAt, shift_actual_end: null }, at(now)), true, `${inAt} at ${now}`)
	}
	assert.equal(sessionIsOpen({ time: "2026-09-24 09:00:00" }, at("2026-09-25 06:01:00")), false)
})

test("no time or a bad time is not an open session", () => {
	assert.equal(sessionIsOpen({}, at("2026-09-25 01:00:00")), false)
	assert.equal(sessionIsOpen({ time: "nonsense" }, at("2026-09-25 01:00:00")), false)
})

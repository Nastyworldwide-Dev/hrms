// H-H3 (21 Sep 2026): PWA Notification `creation` is a naive SITE-clock
// string. Parsed on the device clock, a Malaysian phone against the Dubai site
// showed an approval that just landed as "4 hours ago". Device tz is pinned to
// Kuala Lumpur here via TZ; the clock is faked.
// Run: cd frontend && node --experimental-test-module-mocks --test src/utils/__tests__/siteTime.test.js
process.env.TZ = "Asia/Kuala_Lumpur"

import { test, mock } from "node:test"
import assert from "node:assert/strict"
import dayjs from "dayjs"
import relativeTime from "dayjs/plugin/relativeTime.js"

import { DEFAULT_SITE_TZ, siteTime, siteTimeZone } from "../siteTime.js"

dayjs.extend(relativeTime)

const CREATION = "2026-09-21 10:00:00"
const NOW = new Date("2026-09-21T06:05:00Z") // 10:05 in Dubai, 14:05 in Kuala Lumpur

test("device-clock parsing renders the Dubai approval '4 hours ago' (the defect)", () => {
	mock.timers.enable({ apis: ["Date"], now: NOW })
	assert.equal(dayjs(CREATION).fromNow(), "4 hours ago")
	mock.timers.reset()
})

test("siteTime renders it 'a few minutes ago' with the site on Dubai time", () => {
	mock.timers.enable({ apis: ["Date"], now: NOW })
	assert.equal(siteTimeZone(), DEFAULT_SITE_TZ)
	assert.equal(siteTime(CREATION).fromNow(), "5 minutes ago")
	mock.timers.reset()
})

test("boot's site timezone wins over the fallback", () => {
	globalThis.window = { frappe: { boot: { time_zone: "Asia/Kuala_Lumpur" } } }
	assert.equal(siteTimeZone(), "Asia/Kuala_Lumpur")
	assert.equal(siteTime(CREATION).toISOString(), "2026-09-21T02:00:00.000Z")
	globalThis.window = { frappe: { boot: { sysdefaults: { time_zone: "Europe/Rome" } } } }
	assert.equal(siteTimeZone(), "Europe/Rome")
	delete globalThis.window
})

test("microsecond strings parse (Frappe's default serialisation); garbage stays invalid", () => {
	assert.equal(
		siteTime("2026-09-21 10:00:00.123456").valueOf(),
		Date.UTC(2026, 8, 21, 6, 0, 0, 123)
	)
	assert.equal(siteTime("garbage").isValid(), false)
	assert.equal(siteTime(undefined).isValid(), false)
})

test("a string that already carries Z or an offset is not shifted again", () => {
	assert.equal(siteTime("2026-09-21T06:00:00Z").utc().format("HH:mm"), "06:00")
	assert.equal(siteTime("2026-09-21T10:00:00+04:00").utc().format("HH:mm"), "06:00")
})

// Ticket #4855 (13 Oct 2026, "Cannot set forgot clock out — the app freezes").
// The Forgot to check out sheet started at 18:00 on the check-in day. For a
// check-in after 18:00 that is BEFORE the check-in: the field opened red
// ("Must be after the check-in time") and Send stayed off, which reads as a
// frozen app. Reproduced in WebKit with a 19:30 check-in.
import { test } from "node:test"
import assert from "node:assert/strict"
import { defaultCheckoutTime } from "../checkinSession.js"

const at = (s) => new Date(s)

test("a day check-in starts the sheet at 18:00 that day", () => {
	assert.equal(
		defaultCheckoutTime("2026-10-18 09:00:00", at("2026-10-19T07:00")).getTime(),
		at("2026-10-18T18:00").getTime()
	)
})

test("a check-in after 18:00 starts one minute after the check-in, never before it", () => {
	assert.equal(
		defaultCheckoutTime("2026-10-18 19:30:00", at("2026-10-19T07:00")).getTime(),
		at("2026-10-18T19:31").getTime()
	)
})

test("never in the future", () => {
	const now = at("2026-10-18T12:00")
	assert.equal(defaultCheckoutTime("2026-10-18 09:00:00", now).getTime(), now.getTime())
})

test("no check-in time, no default", () => {
	assert.equal(defaultCheckoutTime("", at("2026-10-19T07:00")), null)
})

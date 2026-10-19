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

test("a check-in under a minute old leaves the time for the person to pick", () => {
	// now would be at or before the check-in once the field drops the seconds,
	// and the sheet would open red again (review of 2e617bb0a).
	assert.equal(defaultCheckoutTime("2026-10-18 09:00:20", at("2026-10-18T09:00:50")), null)
})

test("invariant: the start is empty or after the check-in and not after now", () => {
	// Three fixes hit this function, each a different edge (review of da87de282).
	const base = at("2026-10-18T00:00").getTime()
	for (let inMin = 0; inMin < 24 * 60; inMin += 7) {
		for (const ageMin of [0, 0.5, 1, 2, 90, 600, 1500]) {
			const checkedIn = new Date(base + inMin * 60000)
			const now = new Date(checkedIn.getTime() + ageMin * 60000)
			const pad = (n) => String(n).padStart(2, "0")
			const s = `${checkedIn.getFullYear()}-${pad(checkedIn.getMonth() + 1)}-${pad(
				checkedIn.getDate()
			)} ${pad(checkedIn.getHours())}:${pad(checkedIn.getMinutes())}:00`
			const start = defaultCheckoutTime(s, now)
			if (start === null) continue
			assert.ok(start > checkedIn && start <= now, `${s} at +${ageMin}m gave ${start}`)
		}
	}
})

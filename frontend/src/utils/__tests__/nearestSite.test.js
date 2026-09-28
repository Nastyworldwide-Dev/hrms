// The check-in screen measures against the site the server will judge by
// (28 Sep 2026: HR lets a person check in at more than one site). Inside a
// site -> that site; outside all -> the nearest, like hrms.utils.geofence.
import assert from "node:assert/strict"
import { test } from "node:test"

import { nearestSite } from "../nearestSite.js"

const metres = (a, b) => Math.abs(a.latitude - b.latitude) * 111000
const main = { shift_location: "A", latitude: 3.0, longitude: 101.6, checkin_radius: 100 }
const other = { shift_location: "B", latitude: 3.05, longitude: 101.6, checkin_radius: 100 }

test("inside the second site, the second site is the one shown", () => {
	const here = { latitude: 3.05, longitude: 101.6 }
	assert.equal(nearestSite({ ...main, other_sites: [other] }, here, metres).shift_location, "B")
})

test("outside every site, the nearest is shown", () => {
	const here = { latitude: 3.04, longitude: 101.6 }
	assert.equal(nearestSite({ ...main, other_sites: [other] }, here, metres).shift_location, "B")
})

test("inside the main site, the main site is shown", () => {
	const here = { latitude: 3.0, longitude: 101.6 }
	assert.equal(nearestSite({ ...main, other_sites: [other] }, here, metres).shift_location, "A")
})

test("one site is exactly today", () => {
	const loc = { ...main, strict: true, has_shift_location: true }
	assert.equal(nearestSite(loc, { latitude: 3.5, longitude: 101.6 }, metres), loc)
})

test("the main payload's other fields are kept", () => {
	const here = { latitude: 3.05, longitude: 101.6 }
	const shown = nearestSite(
		{ ...main, strict: true, shift_type: "DAY", other_sites: [other] },
		here,
		metres
	)
	assert.equal(shown.strict, true)
	assert.equal(shown.shift_type, "DAY")
})

test("no position yet shows the main site", () => {
	const loc = { ...main, other_sites: [other] }
	assert.equal(nearestSite(loc, null, metres).shift_location, "A")
})

test("a free site among several wins", () => {
	const free = { ...other, free_location: true }
	const here = { latitude: 3.9, longitude: 101.6 }
	assert.equal(nearestSite({ ...main, other_sites: [free] }, here, metres).shift_location, "B")
})

// Tests for the platform facts behind check-in geolocation.
// Run with: yarn --cwd frontend test
import { test } from "node:test"
import assert from "node:assert/strict"

const {
	GEO_DENIED,
	GEO_INSECURE,
	GEO_TIMEOUT,
	GEO_UNAVAILABLE,
	GEO_UNSUPPORTED,
	describeGeolocationError,
	formatAccuracy,
	geolocationBlockedReason,
} = await import("../geolocation.js")

const fakeWindow = ({ geolocation = {}, isSecureContext = true } = {}) => ({
	navigator: geolocation === null ? {} : { geolocation },
	isSecureContext,
})

test("a secure page with geolocation is not blocked", () => {
	assert.equal(geolocationBlockedReason(fakeWindow()), null)
})

test("http:// is reported as insecure, not as a permission problem", () => {
	// The browser answers PERMISSION_DENIED here, which sent staff off to
	// check permissions they had already granted. Reaching a bench at
	// http://192.168.x.x:8000 from a desk browser is the common way in.
	assert.equal(geolocationBlockedReason(fakeWindow({ isSecureContext: false })), GEO_INSECURE)
})

test("a browser without the API at all is reported as unsupported", () => {
	assert.equal(geolocationBlockedReason(fakeWindow({ geolocation: null })), GEO_UNSUPPORTED)
})

test("no window at all (SSR, tests) is unsupported rather than a crash", () => {
	assert.equal(geolocationBlockedReason(null), GEO_UNSUPPORTED)
})

test("error codes are classified into the three things a person can act on", () => {
	assert.equal(describeGeolocationError({ code: 1 }), GEO_DENIED)
	assert.equal(describeGeolocationError({ code: 3 }), GEO_TIMEOUT)
	assert.equal(describeGeolocationError({ code: 2 }), GEO_UNAVAILABLE)
})

test("an error with no code, or no error, still classifies", () => {
	assert.equal(describeGeolocationError(undefined), GEO_UNAVAILABLE)
	assert.equal(describeGeolocationError({}), GEO_UNAVAILABLE)
})

test("accuracy reads as a radius, and switches unit where metres stop helping", () => {
	assert.equal(formatAccuracy(38.2), "±38 m")
	assert.equal(formatAccuracy(999), "±999 m")
	// A desktop locating itself by IP. Reported, not hidden — it is the whole
	// explanation for a check-in that will need approving.
	assert.equal(formatAccuracy(5400), "±5.4 km")
})

test("a reading with no usable estimate formats as nothing at all", () => {
	for (const value of [null, undefined, 0, -1, "abc", Number.NaN, Number.POSITIVE_INFINITY]) {
		assert.equal(formatAccuracy(value), null, `expected null for ${String(value)}`)
	}
})

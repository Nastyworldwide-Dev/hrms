// Shortcuts to services outside this site (owner's boss, 28 Sep 2026:
// TruTrip on More, with its own icon). Kept apart from APP_LINKS, whose
// same-origin guard must keep refusing external hosts.
import assert from "node:assert/strict"
import { test } from "node:test"

import { EXTERNAL_LINKS, isAllowedExternal, openExternal } from "../externalLinks.js"
import { APP_LINKS, isSameOriginPath } from "../appLinks.js"

test("TruTrip is offered, pointing at its sign-in page", () => {
	const trip = EXTERNAL_LINKS.find((link) => link.key === "trutrip")
	assert.ok(trip, "TruTrip is listed")
	assert.equal(trip.href, "https://app.trutrip.co/v2/login")
	assert.equal(trip.title, "TruTrip")
})

test("every shortcut is https on an allowed host", () => {
	for (const link of EXTERNAL_LINKS) assert.ok(isAllowedExternal(link.href), link.href)
})

test("anything else is refused", () => {
	for (const href of [
		"http://app.trutrip.co/v2/login",
		"https://evil.example/app.trutrip.co",
		"https://app.trutrip.co.evil.example/",
		"javascript:alert(1)",
		"//app.trutrip.co",
		"",
		null,
	]) {
		assert.equal(isAllowedExternal(href), false, String(href))
	}
})

test("it opens in a new tab with no handle back to this app", () => {
	const calls = []
	const opened = openExternal({ href: "https://app.trutrip.co/v2/login" }, (...args) => {
		calls.push(args)
		return {}
	})
	assert.equal(opened, true)
	assert.deepEqual(calls, [["https://app.trutrip.co/v2/login", "_blank", "noopener,noreferrer"]])
})

test("a refused link opens nothing", () => {
	const calls = []
	assert.equal(
		openExternal({ href: "https://evil.example" }, (...a) => calls.push(a)),
		false
	)
	assert.deepEqual(calls, [])
})

test("the same-origin app list still refuses external hosts", () => {
	assert.equal(isSameOriginPath("https://app.trutrip.co/v2/login"), false)
	assert.ok(APP_LINKS.every((link) => !link.href.startsWith("http")))
})

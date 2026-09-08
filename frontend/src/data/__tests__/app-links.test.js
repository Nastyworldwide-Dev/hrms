// The Apps rows on More / SideNav leave the HRMS PWA by full navigation, so
// their targets are plain paths on the same origin. Pin that: a relative path
// would resolve under /hrms/ and 404, and anything host-shaped would make the
// row an open redirect.
import { test } from "node:test"
import assert from "node:assert/strict"

import { APP_LINKS, isSameOriginPath } from "../appLinks.js"

test("every app link is an absolute same-origin path with a label", () => {
	assert.equal(APP_LINKS.length, 3)
	for (const link of APP_LINKS) {
		assert.ok(isSameOriginPath(link.href), `${link.key}: ${link.href}`)
		assert.ok(link.title && link.sublabel, `${link.key} needs title + sublabel`)
	}
})

test("app links do not collide with each other or with the PWA's own scope", () => {
	const hrefs = APP_LINKS.map((l) => l.href)
	assert.equal(new Set(hrefs).size, hrefs.length)
	for (const href of hrefs) assert.ok(!href.startsWith("/hrms"), href)
})

test("isSameOriginPath rejects host-shaped and relative targets", () => {
	for (const bad of ["//evil.example/x", "https://evil.example", "approva", "", "/a b", "/x\\y"]) {
		assert.equal(isSameOriginPath(bad), false, bad)
	}
	assert.equal(isSameOriginPath("/helpdesk/my-tickets"), true)
})

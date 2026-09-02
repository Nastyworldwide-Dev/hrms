// The service worker's notificationclick handler used to be registered only
// inside if(isChrome()), so on Firefox/Safari/Samsung Internet tapping a push
// notification opened nothing. Source-asserted (a service worker can't be run
// under node — it needs self/clients/registration), the same way the SFC tests
// pin behaviour they can't execute. This guards against the handler being
// re-gated behind a browser check.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../../public/sw.js", import.meta.url)), "utf8")

test("notificationclick is registered for every browser, not only Chrome", () => {
	const idx = src.indexOf('addEventListener("notificationclick"')
	assert.ok(idx > 0, "a notificationclick handler exists")
	// the 200 chars before the handler must NOT open an isChrome() gate that
	// wraps it (the bug was `if (isChrome()) { addEventListener(...) }`).
	const before = src.slice(Math.max(0, idx - 200), idx)
	assert.doesNotMatch(before, /if\s*\(\s*isChrome\(\)\s*\)\s*\{\s*$/, "handler must not be gated behind isChrome()")
})

test("the click handler resolves the URL from data OR the action button", () => {
	assert.match(
		src,
		/event\.notification\.data && event\.notification\.data\.url\) \|\| event\.action/,
		"must read data.url (body tap) or event.action (non-Chrome action button)",
	)
})

test("the notification URL is stored on data for every browser", () => {
	// data.url must be set unconditionally, not only in the isChrome branch.
	const dataIdx = src.indexOf('notificationOptions["data"]')
	const chromeIdx = src.indexOf("if (isChrome())")
	assert.ok(dataIdx > 0 && (chromeIdx < 0 || dataIdx < chromeIdx), "data.url set before/without the isChrome branch")
})

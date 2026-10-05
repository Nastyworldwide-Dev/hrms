// A rejection's reason reaches the notification row (5 Oct 2026): "who · when · why". The line is built
// from notificationLine's `reason`, so the row says why without opening the request.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const page = readFileSync(fileURLToPath(new URL("../Notifications.vue", import.meta.url)), "utf8")

test("the row's second line ends with the reason, after who and when", () => {
	assert.match(
		page,
		/meta:\s*\[line\.who,\s*time,\s*line\.reason\]\.filter\(Boolean\)\.join\(" · "\)/
	)
})

test("the reason is read from the line the shared module built, never parsed in the view", () => {
	const script = page.slice(page.indexOf("<script"))
	assert.doesNotMatch(script, /Reason\s*:/, "the view must not re-parse the stored sentence")
})

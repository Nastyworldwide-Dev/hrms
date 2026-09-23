// Plan P1-6 (23 Sep): a notification from the system (Administrator, or a
// user with no employee record) showed a grey "?" as its sender; and "Load
// more" was a plain outline button unlike every other list's control.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const page = readFileSync(fileURLToPath(new URL("../Notifications.vue", import.meta.url)), "utf8")

// Superseded in alpha.5 (23 Sep): a row's icon is what the notification is
// ABOUT (time off, overtime, …), not who sent it, so a system sender can no
// longer draw a "?" at all. The sender's name is in the second line.
test("a row shows the kind of thing it is about, never a sender question mark", () => {
	assert.match(page, /<component :is="kindIcon\(item\)" class="g-row-icon" \/>/)
	assert.match(page, /\|\| Bell/, "anything unknown falls back to the bell")
	assert.doesNotMatch(page, /EmployeeAvatar/)
})

test("Load more is the same control as every other list", () => {
	assert.match(page, /class="g-focusable g-list-more[^"]*"[^>]*@click="loadMore"/)
	assert.doesNotMatch(page, /<Button variant="outline" class="g-touch ml-auto" @click="loadMore">/)
})

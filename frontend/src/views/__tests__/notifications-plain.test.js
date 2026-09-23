// Plan P1-6 (23 Sep): a notification from the system (Administrator, or a
// user with no employee record) showed a grey "?" as its sender; and "Load
// more" was a plain outline button unlike every other list's control.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const page = readFileSync(fileURLToPath(new URL("../Notifications.vue", import.meta.url)), "utf8")

test("a sender with no person shows the Nadi mark, not a question mark", () => {
	assert.match(page, /<GLogo v-if="!getEmployeeInfoByUserID\(item\.from_user\)"/)
	assert.match(page, /<EmployeeAvatar v-else :userID="item\.from_user"/)
})

test("Load more is the same control as every other list", () => {
	assert.match(page, /class="g-focusable g-list-more[^"]*"[^>]*@click="loadMore"/)
	assert.doesNotMatch(page, /<Button variant="outline" class="g-touch ml-auto" @click="loadMore">/)
})

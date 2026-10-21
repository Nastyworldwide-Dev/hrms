// A leave row with no day count shows no dangling dot ("5 Jan ·") (UX review
// 21 Oct 2026, F9), as the other request rows already guard theirs.
// Source-asserted: the node runner does not compile SFCs.
// Run: cd frontend && node --test src/components/__tests__/LeaveRequestItem.test.js
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../LeaveRequestItem.vue", import.meta.url)), "utf8")

test("the dot and the count draw together, or not at all", () => {
	assert.match(
		src,
		/<template v-if="daysWords\(props\.doc\.total_leave_days\)">\s*<span class="whitespace-pre"> &middot; <\/span>/
	)
})

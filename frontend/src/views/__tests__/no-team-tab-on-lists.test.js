// Approvals owns team requests (owner ruling 23 Sep: approvals only where they
// can be done; alpha.4 P2-5). The request lists are the person's OWN history,
// so the per-list "Team Leaves / Team Claims / Team Requests" tabs go: two
// places to find the same request is how one gets decided twice or missed.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

for (const file of ["../leave/List.vue", "../expense_claim/List.vue", "../attendance/ShiftRequestList.vue"]) {
	test(`${file} is your own history only`, () => {
		const src = readFileSync(fileURLToPath(new URL(file, import.meta.url)), "utf8")
		assert.doesNotMatch(src, /Team (Leaves|Claims|Requests)/)
		assert.doesNotMatch(src, /:tabButtons=/)
	})
}

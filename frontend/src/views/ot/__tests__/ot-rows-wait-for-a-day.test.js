// Hours and Note wait for a day (UX review 21 Oct 2026, F5): with nothing to
// claim the form showed three empty rows under "nothing to claim yet".
// Source-asserted: the node runner does not compile SFCs.
// Run: cd frontend && node --test src/views/ot/__tests__/ot-rows-wait-for-a-day.test.js
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../OTRequestForm.vue", import.meta.url)), "utf8")

test("hours and note hide until a day is chosen; the day field stays", () => {
	assert.match(src, /\["claimed_hours", "explanation"\]\.includes\(f\.fieldname\)\) f\.hidden = day \? 0 : 1/)
})

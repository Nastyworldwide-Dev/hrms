// Fix a day asks "Time slip reason" only for a time slip, as the doctype's
// depends_on says (UX review 21 Oct 2026, F7). Source-asserted: the node
// runner does not compile SFCs.
// Run: cd frontend && node --test src/views/attendance/__tests__/AttendanceRequestForm.test.js
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../AttendanceRequestForm.vue", import.meta.url)), "utf8")

test("the time slip reason row hides unless Reason is Time Slip", () => {
	assert.match(src, /f\.fieldname === "time_slip_reason"/)
	assert.match(src, /field\.hidden = reason !== "Time Slip"/)
})

test("a hidden pick is cleared on a new request, so it is never sent", () => {
	assert.match(src, /if \(field\.hidden && !props\.id\) attendanceRequest\.value\.time_slip_reason = undefined/)
})

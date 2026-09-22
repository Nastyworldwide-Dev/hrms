// A rejected OT Request / Replacement Leave Claim showed an "Approved" chip.
// Both doctypes are submitted on rejection too (the decision is recorded in
// `status`, the submit seals it), so a chip that read docstatus alone could
// not tell the two apart. One helper decides the chip for every surface.
// Run: cd frontend && node --test tests/request-status-chip.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { requestStatusChip } from "../src/utils/requestStatus.js"

const read = (rel) =>
	readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8")

test("a submitted request is Approved unless its status says Rejected", () => {
	assert.equal(
		requestStatusChip({ docstatus: 1, status: "Approved" }),
		"Approved"
	)
	assert.equal(
		requestStatusChip({ docstatus: 1, status: "Rejected" }),
		"Rejected"
	)
	// status missing from an older payload: submitted still reads Approved
	assert.equal(requestStatusChip({ docstatus: 1 }), "Approved")
})

test("cancelled and draft requests keep their own chips", () => {
	assert.equal(
		requestStatusChip({ docstatus: 2, status: "Approved" }),
		"Cancelled"
	)
	// ONE waiting word (owner ruling, 21 Sep 2026). This used to assert the
	// doctype's own pending word — Open here, Draft on a Shift Request,
	// Pending on a Remote Checkin Request — which is exactly the three-words-
	// for-one-state the ruling removed. The STORED word is untouched; only the
	// chip changed, and these assertions are about the chip.
	assert.equal(requestStatusChip({ docstatus: 0, status: "Open" }), "Waiting")
	assert.equal(requestStatusChip({ docstatus: 0, status: "Draft" }), "Waiting")
	assert.equal(requestStatusChip({}), "Waiting")
})

test("every request row, the detail header and the OT views use the shared helper", () => {
	for (const rel of [
		"../src/components/LeaveRequestItem.vue",
		"../src/components/AttendanceRequestItem.vue",
		"../src/components/ShiftRequestItem.vue",
		"../src/components/ExpenseClaimItem.vue",
		"../src/components/OTRequestItem.vue",
		"../src/components/ReplacementLeaveClaimItem.vue",
		"../src/components/FormView.vue",
		"../src/views/ot/ReplacementLeave.vue",
	]) {
		const source = read(rel)
		assert.match(
			source,
			/import \{ requestStatus(Chip)? \} from "@\/utils\/requestStatus"/,
			rel
		)
		assert.match(source, /requestStatus(Chip)?\(/, rel)
		// no hand-picked pending word
		assert.doesNotMatch(
			source,
			/docstatus \? props\.doc\.status : ['"](Draft|Open)['"]/,
			rel
		)
		// the chip's variant is looked up from the English word: never hand a
		// translated string to :status (the Malay neutral-chip bug, C-M-6)
		assert.doesNotMatch(source, /:status="__\(/, rel)
		assert.doesNotMatch(source, /return __\(requestStatus/, rel)
		// no chip derived from docstatus alone
		assert.doesNotMatch(source, /docstatus === 1 \? ['"]Approved['"]/, rel)
		assert.doesNotMatch(
			source,
			/docstatus === 1\) return __\("Approved"\)/,
			rel
		)
		assert.doesNotMatch(
			source,
			/no status\/approver field|docstatus-driven model/,
			rel
		)
	}
})

test("the list asks the server for status so the chip has something to read", () => {
	const list = read("../src/views/ot/OTRequestList.vue")
	const fields = list.slice(list.indexOf("const OT_REQUEST_FIELDS"))
	assert.match(fields.slice(0, fields.indexOf("]")), /"status"/)
})

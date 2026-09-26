// Plan P1-5 (23 Sep): the approval sheet spoke the system's language —
// "Leave Application", "ID HR-LAP-2026-02562", a status pill reading "Open".
// Basis W-PLAIN: no doctype names, no record ids in running text. The sheet
// uses the same words as the Approvals list ("Time off") and the one shared
// status rule (utils/requestStatus: "Waiting", "Approved", ...).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const sheet = read("../RequestActionSheet.vue")
const fields = read("../../data/config/requestSummaryFields.js")

test("the heading is the plain kind, not the doctype", () => {
	assert.match(sheet, /:label="__\(kindLabel\)"/)
	assert.match(sheet, /REQUEST_KIND\[document\?\.doctype\]/)
	assert.doesNotMatch(sheet, /\{\{ __\(document\?\.doctype\) \}\}/)
})

test("no record id row in any sheet", () => {
	assert.doesNotMatch(fields, /label: "ID"/)
})

test("status reads from the shared rule, not the raw select value", () => {
	assert.match(sheet, /requestStatus\(props\.modelValue\.doctype, document\.doc\)\.label/)
})

test("one map of plain kinds, the same words the server list uses", () => {
	const map = read("../../utils/requestKind.js")
	for (const [dt, word] of [["Leave Application", "Time off"], ["OT Request", "Overtime"], ["Attendance Request", "Fix a day"]]) {
		assert.match(map, new RegExp(`"${dt}": "${word}"`))
	}
})

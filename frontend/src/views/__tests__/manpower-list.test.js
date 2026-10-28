import assert from "node:assert/strict"
import { test } from "node:test"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

import { stage, STAGE_LABELS } from "../../utils/manpowerRequest.js"

test("M2 List: stage() returns proper label and status for different doc states", () => {
	const docWaiting = {
		status: "Open",
		docstatus: 0,
		hiring_status: undefined,
	}
	const stageWaiting = stage(docWaiting)
	assert.strictEqual(stageWaiting.label, "Waiting for manager")
	assert.strictEqual(stageWaiting.status, "waiting")

	const docNeedsHR = {
		status: "Approved",
		docstatus: 1,
		hiring_status: undefined,
	}
	const stageNeedsHR = stage(docNeedsHR)
	assert.strictEqual(stageNeedsHR.label, "Needs HR")
	assert.strictEqual(stageNeedsHR.status, "waiting")

	const docRecruiting = {
		status: "Approved",
		docstatus: 1,
		hiring_status: "Recruiting",
	}
	const stageRecruiting = stage(docRecruiting)
	assert.strictEqual(stageRecruiting.label, "Recruiting")
	assert.strictEqual(stageRecruiting.status, "in progress")

	const docFilled = {
		status: "Approved",
		docstatus: 1,
		hiring_status: "Filled",
	}
	const stageFilled = stage(docFilled)
	assert.strictEqual(stageFilled.label, "Filled")
	assert.strictEqual(stageFilled.status, "completed")

	const docClosed = {
		status: "Withdrawn",
		docstatus: 1,
		hiring_status: "Recruiting",
	}
	const stageClosed = stage(docClosed)
	assert.strictEqual(stageClosed.label, "Closed")
	assert.strictEqual(stageClosed.status, "withdrawn")
	assert.strictEqual(stageClosed.reason, "Withdrawn")

	const docRejected = {
		status: "Rejected",
		docstatus: 1,
	}
	const stageRejected = stage(docRejected)
	assert.strictEqual(stageRejected.label, "Closed")
	assert.strictEqual(stageRejected.reason, "Rejected")
})

test("M2 List: STAGE_LABELS has the standard vocabulary", () => {
	assert.deepStrictEqual(STAGE_LABELS, [
		"Waiting for manager",
		"Needs HR",
		"Recruiting",
		"Filled",
		"Closed",
	])
})

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("M2 List: owner ruling, ONE name 'Manpower request(s)', no 'staff request' text", () => {
	const list = read("../manpower/ManpowerRequestList.vue")
	assert.match(list, /pageTitle="__\('Manpower requests'\)"/)
	for (const file of [
		list,
		read("../../components/ManpowerRequestItem.vue"),
		read("../manpower/ManpowerHRBoard.vue"),
	])
		assert.doesNotMatch(file, /staff request/i)
})

test("M2 List: the row has an icon tile and a status chip", () => {
	const item = read("../../components/ManpowerRequestItem.vue")
	assert.match(item, /g-row__well--tile/)
	assert.match(item, /<GStatusChip/)
})

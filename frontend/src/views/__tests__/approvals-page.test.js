// The Approvals page (audit-flows 4B; owner ruling 23 Sep: approvals appear
// only where they can be done). One list of everything waiting on me, oldest
// first, and every row opens the SAME request sheet that decides it (Approve,
// or Not approve with a required reason) — no second way to decide.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8")
const page = read("../Approvals.vue")
const template = page.slice(0, page.indexOf("<script"))

test("the page reads the one waiting list from the server", () => {
	assert.match(page, /hrms\.api\.approvals_list\.get_waiting_for_me/)
})

test("each row says who, what, when; the row opens the request sheet", () => {
	assert.match(template, /row\.who/)
	assert.match(template, /row\.kind/)
	assert.match(template, /<RequestActionSheet/)
})

test("an empty queue is one plain line", () => {
	assert.match(template, /__\("Nothing is waiting on you\."\)/)
})

test("the route exists, and Home's waiting rows open it", () => {
	assert.match(read("../../router/index.js"), /name: "Approvals"/)
	assert.match(read("../../components/NeedsYou.vue"), /name: "Approvals"/)
})

test("every type the server can list has fields for the sheet it opens", async () => {
	// Review of be4b81edf: the server lists "Time off in lieu" (Compensatory
	// Leave Request) but the page had no fields for it, so tapping that row
	// threw inside RequestActionSheet — the only way to decide it. The page
	// reads the ONE shared map, and the map covers every listed type.
	// DECIDE_THEN_SUBMIT, not the label map: it is what get_waiting_for_me
	// iterates, and the label map has a fallback, so a type can be listed
	// without a label (review of b16b13f76).
	const server = read("../../../../hrms/api/approval.py")
	const block = server.slice(server.indexOf("DECIDE_THEN_SUBMIT = {")).split("\n}")[0]
	const kinds = [...block.matchAll(/^\t"([^"]+)":/gm)].map((m) => m[1])
	assert.ok(kinds.length >= 7, "the server's list of types was found")
	const { REQUEST_SUMMARY_FIELDS } = await import("../../data/config/requestSummaryFields.js")
	for (const doctype of kinds) {
		assert.ok(Array.isArray(REQUEST_SUMMARY_FIELDS[doctype]), `${doctype} has sheet fields`)
	}
	assert.match(page, /REQUEST_SUMMARY_FIELDS\[selected\.doctype\]/, "the page uses the shared map")
})

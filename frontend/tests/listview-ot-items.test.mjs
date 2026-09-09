// OT Request History and the Replacement Leave Claim list rendered blank rows:
// ListView picks the row component from `listItemComponent[doctype]`, and the
// map had no entry for either doctype, so `<component :is="undefined">`
// rendered nothing. The rows existed — the query returned them — the eye
// just had nothing to look at.
// Run: cd frontend && node --test tests/listview-ot-items.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (rel) =>
	readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8")
const source = read("../src/components/ListView.vue")

test("ListView maps OT Request and Replacement Leave Claim to a row component", () => {
	const start = source.indexOf("const listItemComponent = {")
	assert.notEqual(start, -1, "listItemComponent map exists")
	const map = source.slice(start, source.indexOf("}", start))
	assert.match(map, /"OT Request": markRaw\(OTRequestItem\)/)
	assert.match(
		map,
		/"Replacement Leave Claim": markRaw\(ReplacementLeaveClaimItem\)/
	)
	assert.match(
		source,
		/import OTRequestItem from "@\/components\/OTRequestItem\.vue"/
	)
	assert.match(
		source,
		/import ReplacementLeaveClaimItem from "@\/components\/ReplacementLeaveClaimItem\.vue"/
	)
})

// A sent request shows who it went to, never a blank row (UX review 21 Oct
// 2026, F6): the stored approver was not in the viewer's own option list, so
// the read-only select had nothing to draw. Source-asserted: the node runner
// does not compile SFCs.
// Run: cd frontend && node --test src/components/__tests__/FormField.saved-approver.test.js
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("a saved value outside the option list is added, labelled by its title", () => {
	assert.match(
		read("../FormField.vue"),
		/!props\.documentList\.some\(\(o\) => o\.value === v\)\)\s*return \[\.\.\.props\.documentList, \{ label: props\.display \|\| String\(v\), value: v \}\]/
	)
})

test("the approver's stored name is that title", () => {
	const src = read("../FormView.vue")
	assert.match(src, /leave_approver: \(model\) => model\.leave_approver_name/)
	assert.match(src, /expense_approver: \(model\) => model\.expense_approver_name/)
})

test("an approver nobody set says who sets it", () => {
	assert.match(read("../FormField.vue"), /__\("Not set, ask HR"\)/)
})

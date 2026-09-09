// Cancel on a submitted OT Request / Replacement Leave Claim silently failed:
// FormView pushed `docstatus: 2` through documentResource.setValue, which is
// frappe.client.set_value — and that refuses standard fields. docstatus is a
// transition, not an edit; the server performs it in hrms.api.approval.finalize
// exactly as RequestActionSheet already does.
// Run: cd frontend && node --test tests/formview-cancel-finalize.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const source = readFileSync(
	fileURLToPath(new URL("../src/components/FormView.vue", import.meta.url)),
	"utf8"
)
const fn = source.slice(source.indexOf("async function handleDocUpdate"))
const body = fn.slice(0, fn.indexOf("\n}\n"))

test("submit and cancel are transitions routed through approval.finalize", () => {
	assert.match(
		source,
		/createResource\(\{\s*url: "hrms\.api\.approval\.finalize"/
	)
	assert.match(body, /finalize\.submit\(/)
	assert.match(body, /expected_modified: documentResource\.doc\?\.modified/)
	assert.match(body, /docstatus: action === "submit" \? 1 : 2/)
})

test("docstatus is never written through set_value", () => {
	assert.doesNotMatch(body, /params\.docstatus = [12]/)
})

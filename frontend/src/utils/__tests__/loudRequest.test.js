// A link-picker typeahead failure must not raise a page-level toast.
//
// On the expense claim form, `frappe.desk.search.search_link` 403s for Account,
// Currency, Branch and Location. Each failure toasted "Could not load —
// Insufficient Permission for Account" at bottom-centre, which is exactly where
// the sticky primary button sits: the screen's only submit control was covered
// by an error written in backend vocabulary. Observed in the 8.x frontend audit
// (docs/glass/frontend-audit.md, expense-claims-new__390-dark.png).
//
// loudRequest imports `toast` from frappe-ui, whose barrel cannot resolve under
// plain node, so frappe-ui is module-mocked. Run with:
//   node --experimental-test-module-mocks --test "frontend/**/*.test.js"
import { test, mock } from "node:test"
import assert from "node:assert/strict"

mock.module("frappe-ui", { namedExports: { toast: () => {} } })
const { makeLoudRequest } = await import("../loudRequest.js")

const PERMISSION_ERROR = {
	exc_type: "PermissionError",
	messages: ["Insufficient Permission for Account"],
}

function harness(error = PERMISSION_ERROR) {
	const toasts = []
	let clock = 0
	const loud = makeLoudRequest(() => Promise.reject(error), {
		notify: (t) => toasts.push(t),
		// step well past the repeat-suppression window each call, so a missing
		// toast is never an artifact of de-duplication
		now: () => (clock += 60_000),
	})
	return { loud, toasts }
}

test("a link-picker search failure is logged but never toasted", async () => {
	const { loud, toasts } = harness()
	await assert.rejects(() => loud({ url: "/api/method/frappe.desk.search.search_link" }))
	assert.deepEqual(toasts, [], "search_link must not raise a user-facing toast")
})

test("the same failure on any other endpoint still toasts", async () => {
	const { loud, toasts } = harness()
	await assert.rejects(() => loud({ url: "/api/method/hrms.api.get_expense_claims" }))
	assert.equal(toasts.length, 1, "unrelated endpoints keep their loud failure")
	assert.equal(toasts[0].title, "Could not load")
})

test("silencing the toast does not swallow the rejection", async () => {
	const { loud } = harness()
	await assert.rejects(
		() => loud({ url: "/api/method/frappe.desk.search.search_link" }),
		(e) => e.exc_type === "PermissionError"
	)
})

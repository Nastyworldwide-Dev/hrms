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
// plain Node or Bun. Replace only that UI import; execute the real request logic.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const source = readFileSync(new URL("../loudRequest.js", import.meta.url), "utf8").replace(
	'import { toast } from "frappe-ui"',
	"const toast = () => {}"
)
const makeLoudRequest = new Function(
	`${source.replace("export function", "function")}\nreturn makeLoudRequest`
)()

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

test("a detail-form attachment fetch failure is logged but never toasted", async () => {
	// A boss opening a notification for a request not routed to him 403s on both
	// the document AND get_attachments; the form's own "could not open" screen is
	// the feedback, so the parallel attachment failure must stay silent.
	const { loud, toasts } = harness()
	await assert.rejects(() => loud({ url: "/api/method/hrms.api.get_attachments" }))
	assert.deepEqual(toasts, [], "get_attachments must not raise a user-facing toast")
})

test("a late check-out submit failure is not toasted twice", async () => {
	// The dialog catches the rejection and shows "Could not submit" with the
	// server's reason. The seam's own "Could not load" on top of it is what HR
	// photographed: two red toasts for one refused submission, the first one
	// titled as if a page had failed to load.
	const { loud, toasts } = harness({
		exc_type: "ValidationError",
		messages: [
			"Check-out time must be before your next check-in EMP-CKIN-2 at 2026-09-02 08:55:44.",
		],
	})
	await assert.rejects(() =>
		loud({ url: "/api/method/hrms.api.remote_checkin.submit_late_checkout" })
	)
	assert.deepEqual(toasts, [], "submit_late_checkout reports through its own dialog")
})

test("the same failure on any other endpoint still toasts", async () => {
	const { loud, toasts } = harness()
	await assert.rejects(() => loud({ url: "/api/method/hrms.api.get_expense_claims" }))
	assert.equal(toasts.length, 1, "unrelated endpoints keep their loud failure")
	assert.equal(toasts[0].title, "Could not load")
})

test("ordinary checkout leaves its error to the sheet without a duplicate load toast", async () => {
	const error = {
		exc_type: "ValidationError",
		messages: ["Only the assigned approver or an HR Manager can approve/reject this request."],
	}
	const { loud, toasts } = harness(error)
	for (const url of [
		"hrms.api.remote_checkin.punch",
		"/api/method/hrms.api.remote_checkin.punch",
	]) {
		await assert.rejects(
			() => loud({ url }),
			(received) => received === error
		)
	}
	assert.deepEqual(toasts, [], "CheckInPanel must remain the sole presenter of the punch error")
})

test("silencing the toast does not swallow the rejection", async () => {
	const { loud } = harness()
	await assert.rejects(
		() => loud({ url: "/api/method/frappe.desk.search.search_link" }),
		(e) => e.exc_type === "PermissionError"
	)
})

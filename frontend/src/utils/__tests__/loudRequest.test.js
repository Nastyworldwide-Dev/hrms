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

// The real isNoAccess (utils/sessionLost.js, no imports) rides along; the person's cookie is
// the other boundary, so `signedIn` is a switch the tests flip.
const session = { user: "a@x" }
const noAccessSource = readFileSync(new URL("../sessionLost.js", import.meta.url), "utf8")
const source = readFileSync(new URL("../loudRequest.js", import.meta.url), "utf8")
	.replace('import { gToast } from "@/components/glass/toast"', "const gToast = () => {}")
	.replace('import { isNoAccess } from "@/utils/sessionLost"', "")
	.replace('import { sessionUser } from "@/utils/personalCache"', "")
const { makeLoudRequest, firstMessage, saveFailedSentence } = new Function(
	"sessionUser",
	`${noAccessSource.replace(/export function/g, "function")}\n${source.replace(
		/export function/g,
		"function"
	)}\nreturn { makeLoudRequest, firstMessage, saveFailedSentence }`
)(() => session.user)

const PERMISSION_ERROR = {
	exc_type: "PermissionError",
	messages: ["Insufficient Permission for Account"],
}

// The default failure is NOT a refusal: a PermissionError from a signed-in person is answered by the
// screen (L1a, below) and never toasted, which would make every "this endpoint is silent" and "this
// one still toasts" test here pass or fail for that reason alone.
const LOAD_ERROR = {
	exc_type: "OperationalError",
	messages: ["Insufficient Permission for Account"],
}

function harness(error = LOAD_ERROR) {
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

test("a refused request decision is not toasted twice", async () => {
	// RequestActionSheet's onActionError already shows "Error" with the
	// server's reason. Managers photographed BOTH toasts stacked — "Could not
	// load" on top of "Error", same sentence twice — on every refused Approve
	// (21 Sep 2026, "No attendance to create …").
	const { loud, toasts } = harness({
		exc_type: "ValidationError",
		messages: ["No attendance to create: 07-08-2026 (Attendance status unchanged)."],
	})
	await assert.rejects(() => loud({ url: "/api/method/hrms.api.approval.decide" }))
	assert.deepEqual(toasts, [], "decide reports through the action sheet's own toast")
})

test("a refused plain submit or cancel is not toasted twice either", async () => {
	// finalize is the decision-less transition on the same sheet, wired to the
	// same onActionError — the same two toasts, just not photographed yet.
	const { loud, toasts } = harness({ exc_type: "ValidationError", messages: ["Refused."] })
	await assert.rejects(() => loud({ url: "/api/method/hrms.api.approval.finalize" }))
	assert.deepEqual(toasts, [], "finalize reports through the action sheet's own toast")
})

test("the same failure on any other endpoint still toasts", async () => {
	const { loud, toasts } = harness()
	await assert.rejects(() => loud({ url: "/api/method/hrms.api.get_expense_claims" }))
	assert.equal(toasts.length, 1, "unrelated endpoints keep their loud failure")
	assert.equal(toasts[0].title, "Something didn't load")
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
	const { loud } = harness(PERMISSION_ERROR)
	await assert.rejects(
		() => loud({ url: "/api/method/frappe.desk.search.search_link" }),
		(e) => e.exc_type === "PermissionError"
	)
})

test("a comparison in a refusal is kept as written; only real tags are stripped", () => {
	// reviews of 96ac1b8e1 and f35e2b982: the text was cut or garbled around < and >. Safety for
	// the v-html toast now lives in glass/toast.js (it escapes); this reader only makes words.
	// ceiling: "a<b and c>d" is a well-formed <b> tag to any parser, so it is stripped; upgrade:
	// stop stripping here altogether once every caller renders as text (toast.js already does).
	for (const [raw, out] of [
		["Hours must be < 8", "Hours must be < 8"],
		["Hours must be > 0", "Hours must be > 0"],
		["x <= 5 and y >= 2", "x <= 5 and y >= 2"],
		["Go -> next", "Go -> next"],
		["Ask <b>HR</b> now", "Ask HR now"],
		["<!-- note -->Refused", "Refused"],
	]) {
		assert.equal(firstMessage({ messages: [raw] }), out, raw)
	}
})

test("a server refusal split by <br>, paragraphs or list items keeps a space between its parts", () => {
	// review of 3169ca158: tags were stripped with nothing in their place, so a Frappe throw
	// "Line one<br>Line two" read "Line oneLine two"
	assert.equal(
		firstMessage({ messages: ["Leave overlaps<br>Pick other days"] }),
		"Leave overlaps Pick other days"
	)
	assert.equal(firstMessage({ messages: ["<p>First.</p><p>Second.</p>"] }), "First. Second.")
	assert.equal(firstMessage({ messages: ["<ul><li>One</li><li>Two</li></ul>"] }), "One Two")
	assert.equal(firstMessage({ messages: ["Ask <b>HR</b> to change it."] }), "Ask HR to change it.")
})

test("firstMessage is the one reader of a server refusal, shared with the forms", () => {
	assert.equal(
		firstMessage({ messages: ["Insufficient leave balance"] }),
		"Insufficient leave balance"
	)
	assert.equal(firstMessage({ message: "Network down" }), "Network down")
	assert.equal(firstMessage(undefined), "Request failed")
	// a caller's own wording stands in only when there is no message at all
	assert.equal(firstMessage(undefined, "Try again."), "Try again.")
	assert.equal(firstMessage({ messages: ["Refused"] }, "Try again."), "Refused")
	// the toast renders with v-html: a Desk link in the refusal must arrive as text
	assert.equal(
		firstMessage({
			messages: ['Already applied: <a href="/app/leave-application/HR-LAP-1">HR-LAP-1</a>'],
		}),
		"Already applied: HR-LAP-1"
	)
})

// Audit F-6 / APP-6: a failed READ toasted the raw server sentence — "User
// nurul.aisyah@… does not have doctype access via role permission for
// document DocType" — to an employee, and at 320px it covered half the screen.
// A load toast now says one plain thing; the server's words go to the console.
test("a failed load toasts plain words, never the server's sentence", async () => {
	const raw = {
		exc_type: "ValidationError",
		messages: ["User a@b.c does not have doctype access via role permission for document DocType"],
	}
	const { loud, toasts } = harness(raw)
	await loud({ url: "hrms.api.some_read" }).catch(() => {})
	assert.equal(toasts.length, 1)
	assert.doesNotMatch(toasts[0].text, /doctype|role permission|@/i)
	assert.equal(toasts[0].title, "Something didn't load")
	// Not "pull down": forms, dialogs and desktop have no pull-to-refresh.
	assert.equal(toasts[0].text, "Try again in a moment.")
})

test("a read whose screen shows its own error is not toasted a second time", async () => {
	const { loud, toasts } = harness()
	await assert.rejects(() =>
		loud({ url: "/api/method/hrms.api.announcements.home_announcements" })
	)
	assert.equal(toasts.length, 0)
})

test("a write whose caller shows the server's reason is not toasted twice", async () => {
	for (const url of [
		"hrms.api.upload_base64_file",
		"hrms.api.delete_attachment",
		"frappe.model.workflow.apply_workflow",
		// TicketDetail.send toasts "Reply not sent" with the server's reason (L1a: the seam no
		// longer speaks for a refusal, so the caller must, once, for every kind of failure)
		"hrms.api.helpdesk.reply",
	]) {
		const { loud, toasts } = harness()
		await assert.rejects(() => loud({ url: `/api/method/${url}` }))
		assert.equal(toasts.length, 0, url)
	}
})

// Owner ruling R4 (6 Oct): a submit made offline says so plainly; nothing is
// queued. Review of the first cut: "Failed to fetch" is ALSO a server that is
// down or restarting while the phone is online, and "your form is kept" is
// only true where a form is open. So: a network failure reads as a network
// failure everywhere (firstMessage); the "form is kept" sentence belongs to the
// form-save sites (saveFailedSentence); and the generic toast is held back only
// when the phone really is offline (the banner already says it).
const NO_NETWORK = new TypeError("Failed to fetch")
const withOnline = (online, fn) => {
	const had = Object.getOwnPropertyDescriptor(globalThis, "navigator")
	Object.defineProperty(globalThis, "navigator", { value: { onLine: online }, configurable: true })
	const restore = () => {
		if (had) Object.defineProperty(globalThis, "navigator", had)
		else delete globalThis.navigator
	}
	let result
	try {
		result = fn()
	} catch (e) {
		restore()
		throw e
	}
	// an async check restores only after it has finished
	if (result && typeof result.then === "function") return result.finally(restore)
	restore()
	return result
}

test("a network failure reads as plain words everywhere, never 'Failed to fetch'", () => {
	withOnline(false, () => assert.equal(firstMessage(NO_NETWORK), "No connection."))
	withOnline(true, () => assert.equal(firstMessage(NO_NETWORK), "Could not reach the server."))
	withOnline(false, () =>
		assert.equal(
			firstMessage(new Error("NetworkError when attempting to fetch resource.")),
			"No connection."
		)
	)
	withOnline(false, () =>
		assert.equal(firstMessage(new TypeError("Load failed")), "No connection.")
	)
})

test("a server refusal still reads as the server's sentence", () => {
	assert.equal(firstMessage(PERMISSION_ERROR), "Insufficient Permission for Account")
})

test("a form save that never reached the server says the form is kept, and may not have been sent", () => {
	withOnline(false, () =>
		assert.equal(
			saveFailedSentence(NO_NETWORK),
			"You are offline, so it may not have been sent. What you typed is still here."
		)
	)
	withOnline(true, () =>
		assert.equal(
			saveFailedSentence(NO_NETWORK),
			"The server could not be reached, so it may not have been sent. What you typed is still here."
		)
	)
	assert.equal(saveFailedSentence(PERMISSION_ERROR), "Insufficient Permission for Account")
})

test("offline: the generic toast is held back, the banner already says it", async () => {
	await withOnline(false, async () => {
		const { loud, toasts } = harness(NO_NETWORK)
		await assert.rejects(loud({ url: "/api/method/frappe.client.insert" }))
		assert.equal(toasts.length, 0)
	})
})

test("online but the server unreachable: the toast still shows (no banner would)", async () => {
	await withOnline(true, async () => {
		const { loud, toasts } = harness(NO_NETWORK)
		await assert.rejects(loud({ url: "/api/method/frappe.client.get_list" }))
		assert.equal(toasts.length, 1)
	})
})

// L1a (alpha.38): "You can't open this." (ResourceError, alpha.37 B2) was followed by a second
// toast, "Something didn't load. Try again in a moment." -- the same refusal reported twice, the
// second one as a glitch that a retry could fix. The refusal belongs to the screen that owns it.
// the repeat window is module state: every call here reads a fresh endpoint
let n = 0
const read = () => `/api/method/hrms.api.l1a_read_${++n}`

const forbidden = (extra = {}) =>
	Object.assign(new Error("x"), {
		response: { status: 403 },
		exc_type: "PermissionError",
		messages: ["User a@x does not have permission to access this document"],
		...extra,
	})

test("a refusal of this page, from a signed-in person, is not toasted on top of its own sentence", async () => {
	for (const error of [
		forbidden(),
		Object.assign(new Error("x"), { exc_type: "PermissionError" }),
	]) {
		const { loud, toasts } = harness(error)
		await assert.rejects(
			() => loud({ url: read(), noAccessShown: true }),
			(received) => received === error,
			"the rejection still reaches the resource, which draws 'You can't open this.'"
		)
		await new Promise((r) => setTimeout(r, 5))
		assert.deepEqual(toasts, [], "no second toast after 'You can't open this.'")
	}
})

// Review of L1a: holding back EVERY signed-in refusal left screens that draw nothing of their own
// silent. A refusal still gets a voice: the plain "You can't open this." toast, never the
// glitch-like "Something didn't load. Try again". Screens that draw the sentence themselves
// (FormView, ResourceError) set `noAccessShown` on the request and get no toast on top.
test("a refusal on a screen that does not draw its own sentence says 'You can't open this.'", async () => {
	const { loud, toasts } = harness(forbidden())
	await assert.rejects(() => loud({ url: read() }))
	await new Promise((r) => setTimeout(r, 5)) // the decision waits one frame for the screen to draw
	assert.equal(toasts.length, 1)
	assert.equal(toasts[0].title, "You can't open this.")
	assert.doesNotMatch(JSON.stringify(toasts[0]), /Try again|didn't load/)
})

test("a screen that draws the sentence itself gets no toast on top", async () => {
	const { loud, toasts } = harness(forbidden())
	await assert.rejects(() => loud({ url: read(), noAccessShown: true }))
	await new Promise((r) => setTimeout(r, 5))
	assert.deepEqual(toasts, [])
})

test("a 403 from a session that has ended still toasts: that screen is on its way to Login", async () => {
	const saved = session.user
	session.user = null
	try {
		const { loud, toasts } = harness(forbidden())
		await assert.rejects(() => loud({ url: read() }))
		assert.equal(toasts.length, 1)
	} finally {
		session.user = saved
	}
})

test("a 401, or a Guest permission error, is never a refusal, even carrying a 403", async () => {
	// (AuthenticationError and SessionExpired are already silent: the redirect to Login says it.)
	for (const error of [
		Object.assign(new Error("x"), { response: { status: 401 } }),
		forbidden({ exc_type: "PermissionError:Guest" }),
	]) {
		const { loud, toasts } = harness(error)
		await assert.rejects(() => loud({ url: read() }))
		assert.equal(toasts.length, 1)
	}
})

test("a server error or a missing document is not a refusal: it keeps the load toast", async () => {
	for (const error of [
		Object.assign(new Error("x"), { response: { status: 500 } }),
		{ exc_type: "DoesNotExistError", messages: ["not found"] },
	]) {
		const { loud, toasts } = harness(error)
		await assert.rejects(() => loud({ url: read() }))
		assert.equal(toasts.length, 1)
	}
})

test("a suppressed refusal does not use up the repeat window of the endpoint", async () => {
	// 1 s apart, inside the 5 s window: only a REPORTED failure may start the window.
	let clock = 0
	const toasts = []
	let error = forbidden()
	const loud = makeLoudRequest(() => Promise.reject(error), {
		notify: (t) => toasts.push(t),
		now: () => (clock += 1000),
	})
	const url = read()
	await assert.rejects(() => loud({ url }))
	error = new Error("boom")
	await assert.rejects(() => loud({ url }))
	assert.equal(toasts.length, 1)
})

test("a screen that has drawn 'You can't open this.' (data-no-access) is not toasted over", async () => {
	globalThis.document = { querySelector: (sel) => (sel.endsWith("[data-no-access]") ? {} : null) }
	try {
		const { loud, toasts } = harness(forbidden())
		await assert.rejects(() => loud({ url: read() }))
		await new Promise((r) => setTimeout(r, 5))
		assert.deepEqual(toasts, [])
	} finally {
		delete globalThis.document
	}
})

test("a 'You can't open this.' left on a hidden page does not silence the current one", async () => {
	// Ionic keeps earlier pages mounted (class ion-page-hidden); only the visible page counts
	let asked = ""
	globalThis.document = { querySelector: (sel) => ((asked = sel), null) }
	try {
		const { loud, toasts } = harness(forbidden())
		await assert.rejects(() => loud({ url: read() }))
		await new Promise((r) => setTimeout(r, 5))
		assert.match(asked, /:not\(\.ion-page-hidden\)/, "the check skips hidden pages")
		assert.equal(toasts.length, 1)
	} finally {
		delete globalThis.document
	}
})

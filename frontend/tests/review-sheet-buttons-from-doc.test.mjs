// Approve/Reject come from the document's state, not from a whole-doc JSON
// equality (audit 21 Sep 2026, C-H-6): any local field touch — a formatter
// writing a display value onto the doc — silently removed both buttons with no
// message. The revision guard is `modified`, which is what the server checks
// too (expected_modified). And a second tap while a decision is in flight is
// ignored (C-H-4).
// Run: cd frontend && node --test tests/review-sheet-buttons-from-doc.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import vm from "node:vm"
import {
	computed,
	ref,
	reactive,
	shallowRef,
	watch,
	effectScope,
	nextTick,
} from "vue"
import { requestStatus } from "../src/utils/requestStatus.js"

const source = (path) => readFileSync(new URL(path, import.meta.url), "utf8")
const executable = (text) =>
	text
		.replace(/^import\s+[\s\S]*?from\s+["'][^"']+["']\s*\n/gm, "")
		.replace(/export default /g, "")
		.replace(/export /g, "")
const tick = async () => {
	await nextTick()
	await Promise.resolve()
	await Promise.resolve()
}

function capability(extraFields = {}) {
	const requests = []
	const scope = effectScope()
	const context = vm.createContext({
		computed,
		ref,
		reactive,
		shallowRef,
		watch,
		Event,
		console: { debug() {}, warn() {}, info() {} },
		getConfig: () => undefined,
		saveLocal() {},
		request: (options) =>
			new Promise((resolve, reject) =>
				requests.push({ options, resolve, reject })
			),
		document: reactive({
			doc: {
				doctype: "Leave Application",
				name: "REQUEST",
				modified: "2026-09-21 09:00:00",
				docstatus: 0,
				status: "Open",
				employee: "STAFF",
				...extraFields,
			},
		}),
	})
	context.document.originalDoc = JSON.parse(
		JSON.stringify(context.document.doc)
	)
	vm.runInContext(
		executable(source("../node_modules/frappe-ui/src/resources/resources.js")),
		context
	)
	vm.runInContext(
		executable(source("../src/composables/decisionCapability.js")),
		context
	)
	scope.run(() =>
		vm.runInContext(
			`var capability = useDecisionCapability(() => document, () => ({ doctype: "Leave Application", name: "REQUEST" }))`,
			context
		)
	)
	return {
		context,
		requests,
		actions: () =>
			Array.from(vm.runInContext("capability.actions.value", context)),
		stop: () => scope.stop(),
	}
}

test("a local field touch keeps Approve/Reject; only a new revision withdraws them", async () => {
	const state = capability()
	assert.equal(state.requests.length, 1)
	state.requests[0].resolve({
		actions: ["Approved", "Rejected"],
		modified: "2026-09-21 09:00:00",
	})
	await tick()
	assert.deepEqual(state.actions(), ["Approved", "Rejected"])

	// a formatter writes a display value onto the doc — not a revision, and not
	// one of the server's fields (an edit to one of THOSE still refuses: see
	// decision-capability.test.mjs "refuses same-revision local edits")
	state.context.document.doc.total_leave_days_display = "2d"
	await tick()
	assert.deepEqual(
		state.actions(),
		["Approved", "Rejected"],
		"a local touch must not hide the buttons"
	)
	assert.equal(state.requests.length, 1, "and must not refetch capability")

	// the server saved a new revision (a reload moves doc and its snapshot):
	// the old capability is withdrawn and re-checked for the new revision
	state.context.document.doc.modified = "2026-09-21 09:05:00"
	state.context.document.originalDoc = JSON.parse(
		JSON.stringify(state.context.document.doc)
	)
	await tick()
	assert.deepEqual(
		state.actions(),
		[],
		"stale capability is withdrawn on a new revision"
	)
	assert.equal(state.requests.length, 2, "and re-checked for the new revision")
	state.stop()
})

test("an untouched doc with a child table (Expense Claim rows) keeps Approve/Reject", async () => {
	// originalDoc is frappe-ui's JSON deep copy: the same rows, never the same
	// reference. A reference compare read every Expense Claim as edited and
	// withheld both buttons (verifier, 21 Sep 2026).
	const state = capability({
		expenses: [{ expense_type: "Travel", amount: 10 }],
	})
	state.requests[0].resolve({
		actions: ["Approved", "Rejected"],
		modified: "2026-09-21 09:00:00",
	})
	await tick()
	assert.deepEqual(state.actions(), ["Approved", "Rejected"])
	// a real edit to a row is still an edit
	state.context.document.doc.expenses[0].amount = 99
	await tick()
	assert.deepEqual(state.actions(), [], "an edited row still refuses")
	state.stop()
})

test("the sheet shows Approve/Reject from the doc's pending state, not from a hand-typed status list", () => {
	const sheet = source("../src/components/RequestActionSheet.vue")
	assert.doesNotMatch(
		sheet,
		/\['Open', 'Draft'\]\.includes\(document\?\.doc\?\.\[approvalField\]\)/
	)
	assert.match(sheet, /requestStatus\(/)
	assert.match(sheet, /isPending && hasPermission\('approval'\)/)
	// the decided-draft Submit row and the actions row both wait on the in-flight flag
	assert.doesNotMatch(
		source("../src/composables/decisionCapability.js"),
		/JSON\.stringify\(doc\)/
	)
	// the doc → pending rule is the shared one
	assert.equal(
		requestStatus("Leave Application", { status: "Open", docstatus: 0 })
			.pending,
		true
	)
	assert.equal(
		requestStatus("Leave Application", { status: "Approved", docstatus: 0 })
			.pending,
		true
	)
	assert.equal(
		requestStatus("Leave Application", { status: "Approved", docstatus: 1 })
			.pending,
		false
	)
})

test("a second tap while a decision is in flight is ignored", () => {
	// updateDocumentStatus returns early on `submitting`; the guard is the first
	// clause so no later check (permissions, revision) can let a double tap through
	const sheet = source("../src/components/RequestActionSheet.vue")
	const fn = sheet.slice(sheet.indexOf("const updateDocumentStatus"))
	const guard = fn.slice(fn.indexOf("if ("), fn.indexOf("return"))
	assert.match(
		guard,
		/^if \(\s*submitting\.value \|\|/,
		"submitting is the first clause of the guard"
	)
	assert.match(sheet, /const submitting = computed\(/)
	// every action button carries the flag
	const buttons = sheet.match(/:disabled="submitting"/g) || []
	assert.ok(
		buttons.length >= 4,
		`expected the four decision buttons to be disabled in flight, got ${buttons.length}`
	)
})

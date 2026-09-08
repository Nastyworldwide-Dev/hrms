import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import vm from "node:vm"
import { createRequire } from "node:module"
import {
	computed,
	ref,
	reactive,
	shallowRef,
	watch,
	effectScope,
	nextTick,
} from "vue"

const require = createRequire(import.meta.url)
const { parse } = require("acorn")
const source = (path) => readFileSync(new URL(path, import.meta.url), "utf8")
const script = (path) =>
	source(path).split("<script setup>")[1].split("</script>")[0]
function declaration(path, name) {
	const text = script(path)
	const node = parse(text, {
		ecmaVersion: "latest",
		sourceType: "module",
	}).body.find(
		(node) =>
			node.id?.name === name ||
			node.declarations?.some((item) => item.id.name === name)
	)
	return node ? text.slice(node.start, node.end) : ""
}
const sheet = "../src/components/RequestActionSheet.vue"
const form = "../src/components/FormView.vue"
const types = [
	"Leave Application",
	"Expense Claim",
	"Shift Request",
	"OT Request",
	"Attendance Request",
	"Replacement Leave Claim",
]

test("all six PWA sheets use server authority instead of a phantom approval permission", () => {
	for (const doctype of types) {
		for (const allowed of [false, true]) {
			const context = vm.createContext({
				props: { modelValue: { doctype, name: "REQUEST" } },
				document: { doc: { employee: "STAFF" } },
				sessionEmployee: { data: { name: "MANAGER" } },
				settings: { data: {} },
				permittedWriteFields: { data: ["status", "approval_status"] },
				approvalField: {
					value: doctype === "Expense Claim" ? "approval_status" : "status",
				},
				docPermissions: {
					data: { permissions: { read: 1, write: 1, submit: 1, cancel: 1 } },
				},
				decisionCapability: {
					actions: ref(allowed ? ["Approved", "Rejected"] : []),
				},
				workflow: ref(null),
			})
			vm.runInContext(declaration(sheet, "hasPermission"), context)
			assert.equal(
				Boolean(vm.runInContext("hasPermission('approval')", context)),
				allowed,
				doctype
			)
		}
	}
})

test("the visible Review action opens the decision sheet for a routed manager without field grants", () => {
	for (const doctype of types) {
		const context = vm.createContext({
			computed,
			props: { id: "REQUEST", doctype },
			isFormDirty: ref(false),
			workflow: ref(null),
			REQUEST_SUMMARY_FIELDS: Object.fromEntries(types.map((dt) => [dt, []])),
			formModel: ref({
				doctype,
				name: "REQUEST",
				docstatus: 0,
				status: "Open",
				approval_status: "Draft",
				employee: "STAFF",
			}),
			employee: { data: { name: "MANAGER" } },
			permittedWriteFields: { data: [] },
			decisionCapability: { actions: ref(["Approved", "Rejected"]) },
			reviewRequest: ref(null),
			showReviewSheet: ref(false),
			console,
		})
		vm.runInContext(
			["REVIEW_DECISION_FIELD", "canReview", "openReviewSheet"]
				.map((name) => declaration(form, name))
				.join("\n"),
			context
		)
		assert.equal(vm.runInContext("canReview.value", context), true, doctype)
		vm.runInContext("openReviewSheet()", context)
		assert.equal(context.showReviewSheet.value, true)
		assert.equal(context.reviewRequest.value.name, "REQUEST")
		context.isFormDirty.value = true
		context.showReviewSheet.value = false
		vm.runInContext("openReviewSheet()", context)
		assert.equal(
			context.showReviewSheet.value,
			false,
			"stale Review click cannot open an edited form"
		)
	}
})

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
function liveSheet(doctype = "OT Request", nativeDocument = false) {
	const requests = [],
		successes = [],
		alerts = []
	const scope = effectScope()
	const context = vm.createContext({
		computed,
		ref,
		reactive,
		shallowRef,
		watch,
		Event,
		toast: (value) => alerts.push(value),
		__: (text) => text,
		console: { debug() {}, warn() {} },
		getConfig: () => undefined,
		saveLocal: (key) =>
			assert.equal(key, null, "approval capability must not be persisted"),
		request: (options) =>
			new Promise((resolve, reject) =>
				requests.push({ options, resolve, reject })
			),
		props: reactive({ modelValue: { doctype, name: "REQUEST" } }),
		document: reactive({
			doc: {
				doctype,
				name: "REQUEST",
				modified: "2026-09-08 12:00:00",
				docstatus: 0,
				status: "Open",
				approval_status: "Draft",
				employee: "STAFF",
			},
			reload() {},
		}),
		workflow: ref(null),
		docPermissions: { data: { permissions: { read: 1 } } },
		onActionError: () => () => {},
		onActionSuccess: (value) => successes.push(value),
	})
	context.document.originalDoc = JSON.parse(
		JSON.stringify(context.document.doc)
	)
	vm.runInContext(
		executable(source("../node_modules/frappe-ui/src/resources/resources.js")),
		context
	)
	if (nativeDocument) {
		Object.assign(context, {
			debounce: () => () =>
				assert.fail("Debounced writes are outside this read-only fixture"),
			getLocal: async () => null,
			deleteLocal() {},
			saveLocal() {},
			updateRowInListResource() {},
			deleteRowInListResource() {},
			revertRowInListResource() {},
			onDocUpdate() {},
		})
		vm.runInContext(
			executable(
				source("../node_modules/frappe-ui/src/resources/documentResource.js")
			),
			context
		)
		const initial = JSON.parse(JSON.stringify(context.document.doc))
		context.initial = initial
		scope.run(() =>
			vm.runInContext(
				"document = createDocumentResource({doctype: initial.doctype, name: initial.name, auto: false})",
				context
			)
		)
		context.document.doc = initial
		context.document.originalDoc = JSON.parse(JSON.stringify(initial))
	}
	vm.runInContext(
		executable(source("../src/composables/decisionCapability.js")),
		context
	)
	scope.run(() =>
		vm.runInContext(
			[
				"decisionCapability",
				"decision",
				"finalize",
				"submitting",
				"hasPermission",
				"currentRequest",
				"pendingDecision",
				"confirmDecision",
				"runPendingDecision",
				"updateDocumentStatus",
			]
				.map((name) => declaration(sheet, name))
				.join("\n"),
			context
		)
	)
	return {
		context,
		requests,
		successes,
		alerts,
		stop: () => scope.stop(),
		run: (code) => vm.runInContext(code, context),
	}
}

test("actual Vue and installed resources deliver Approve/Reject with the reviewed revision for all six types", async () => {
	for (const doctype of types) {
		for (const status of ["Approved", "Rejected"]) {
			const state = liveSheet(doctype)
			assert.equal(state.run("hasPermission('approval')"), false)
			assert.equal(
				state.requests[0].options.url,
				"hrms.api.approval.get_decision_actions"
			)
			assert.equal(state.requests[0].options.params.doctype, doctype)
			state.requests[0].resolve({
				actions: ["Approved", "Rejected"],
				modified: "2026-09-08 12:00:00",
			})
			await tick()
			assert.equal(state.run("hasPermission('approval')"), true)
			const pending = state.run(`updateDocumentStatus({status: '${status}'})`)
			state.run(`updateDocumentStatus({status: '${status}'})`)
			assert.equal(
				state.requests.length,
				2,
				"in-flight actions cannot double-fire"
			)
			assert.equal(state.requests[1].options.url, "hrms.api.approval.decide")
			assert.equal(
				state.requests[1].options.params.expected_modified,
				"2026-09-08 12:00:00"
			)
			assert.equal(state.requests[1].options.params.status, status)
			state.requests[1].resolve({ docstatus: 1, status })
			await pending
			assert.equal(state.successes.length, 1)
			state.stop()
		}
	}
})

test("failed or denied capability never permits a direct PWA action", async () => {
	for (const result of [false, null, { ok: false }]) {
		const state = liveSheet()
		state.requests[0].resolve(result)
		await tick()
		state.run("updateDocumentStatus({status: 'Approved'})")
		assert.equal(state.requests.length, 1)
		state.stop()
	}
	const state = liveSheet()
	state.requests[0].reject(new Error("synthetic unavailable capability"))
	await tick()
	assert.equal(state.run("hasPermission('approval')"), false)
	state.stop()
})

test("all completion orders keep only the current revision's capability", async () => {
	const orders = [
		[0, 1, 2],
		[0, 2, 1],
		[1, 0, 2],
		[1, 2, 0],
		[2, 0, 1],
		[2, 1, 0],
	]
	for (const order of orders) {
		for (const latest of [false, true]) {
			const state = liveSheet()
			state.context.document.doc.modified = "2026-09-08 12:01:00"
			state.context.document.originalDoc = JSON.parse(
				JSON.stringify(state.context.document.doc)
			)
			state.context.document.doc.modified = "2026-09-08 12:02:00"
			state.context.document.originalDoc = JSON.parse(
				JSON.stringify(state.context.document.doc)
			)
			assert.equal(state.requests.length, 3)
			for (const index of order) {
				state.requests[index].resolve({
					actions: (index === 2 ? latest : !latest)
						? ["Approved", "Rejected"]
						: [],
					modified: `2026-09-08 12:0${index}:00`,
				})
				await tick()
			}
			assert.equal(state.run("hasPermission('approval')"), latest)
			state.stop()
		}
	}
})

test("navigation and changed confirmation context cannot send a PWA decision", async () => {
	for (const mutate of [
		(state) => {
			state.context.props.modelValue.name = "OTHER"
		},
		(state) => {
			state.context.document.doc.modified = "2026-09-08 12:01:00"
			state.context.document.originalDoc = JSON.parse(
				JSON.stringify(state.context.document.doc)
			)
		},
	]) {
		const state = liveSheet()
		state.requests[0].resolve({
			actions: ["Approved", "Rejected"],
			modified: "2026-09-08 12:00:00",
		})
		await tick()
		state.run("confirmDecision({status: 'Rejected'}, {})")
		mutate(state)
		const current = state.requests.at(-1)
		if (current !== state.requests[0]) {
			current.resolve({
				actions: ["Approved", "Rejected"],
				modified: state.context.document.doc.modified,
			})
			await tick()
		}
		state.run("runPendingDecision()")
		assert.equal(
			state.requests.filter((item) => item.options.url.endsWith(".decide"))
				.length,
			0
		)
		state.stop()
	}
})

test("self-Leave Reject and legacy Submit remain distinct PWA actions", async () => {
	for (const [doctype, status, actions] of [
		["Leave Application", "Open", ["Rejected"]],
		["OT Request", "Approved", ["Submit"]],
	]) {
		const state = liveSheet(doctype)
		state.context.document.doc.status = status
		state.context.document.originalDoc = JSON.parse(
			JSON.stringify(state.context.document.doc)
		)
		state.requests
			.at(-1)
			.resolve({ actions, modified: state.context.document.doc.modified })
		await tick()
		assert.equal(state.run("hasPermission('approve')"), false)
		assert.equal(
			state.run("hasPermission('reject')"),
			actions.includes("Rejected")
		)
		assert.equal(
			state.run("hasPermission('submit')"),
			actions.includes("Submit")
		)
		state.stop()
	}
})

test("capability cannot approve a newer revision the PWA has not displayed", async () => {
	const state = liveSheet()
	state.requests[0].resolve({
		actions: ["Approved", "Rejected"],
		modified: "2026-09-08 12:01:00",
	})
	await tick()
	assert.equal(state.run("hasPermission('approval')"), false)
	assert.equal(state.context.document.doc.modified, "2026-09-08 12:00:00")
	assert.equal(state.alerts.length, 1)
	state.run("updateDocumentStatus({status: 'Approved'})")
	assert.equal(state.requests.length, 1)
	state.stop()
})

test("an own Leave reject-only response opens FormView's actual Review entry", async () => {
	const requests = [],
		scope = effectScope()
	const context = vm.createContext({
		computed,
		ref,
		reactive,
		shallowRef,
		watch,
		Event,
		console: { debug() {}, warn() {} },
		getConfig: () => undefined,
		saveLocal: (key) => assert.equal(key, null),
		request: (options) =>
			new Promise((resolve, reject) =>
				requests.push({ options, resolve, reject })
			),
		props: reactive({ doctype: "Leave Application", id: "REQUEST" }),
		documentResource: reactive({
			doc: {
				doctype: "Leave Application",
				name: "REQUEST",
				modified: "2026-09-08 12:00:00",
				status: "Open",
				docstatus: 0,
				employee: "SELF",
			},
		}),
		employee: { data: { name: "SELF" } },
		formModel: ref({ employee: "SELF" }),
		isFormDirty: ref(false),
		workflow: ref(null),
		REQUEST_SUMMARY_FIELDS: { "Leave Application": [] },
		toast() {},
		__: (text) => text,
	})
	context.documentResource.originalDoc = JSON.parse(
		JSON.stringify(context.documentResource.doc)
	)
	vm.runInContext(
		executable(source("../node_modules/frappe-ui/src/resources/resources.js")),
		context
	)
	vm.runInContext(
		executable(source("../src/composables/decisionCapability.js")),
		context
	)
	const run = (code) => vm.runInContext(code, context)
	scope.run(() =>
		run(
			[
				"decisionCapability",
				"canReview",
				"showReviewSheet",
				"reviewRequest",
				"openReviewSheet",
			]
				.map((name) => declaration(form, name))
				.join("\n")
		)
	)
	assert.equal(run("canReview.value"), false)
	requests[0].resolve({
		actions: ["Rejected"],
		modified: "2026-09-08 12:00:00",
	})
	await tick()
	assert.equal(run("canReview.value"), true)
	run("openReviewSheet()")
	assert.equal(run("showReviewSheet.value"), true)
	assert.equal(run("reviewRequest.value.name"), "REQUEST")
	context.isFormDirty.value = true
	assert.equal(run("canReview.value"), false)
	scope.stop()
})

test("own draft action bars do not hide a legitimate self-rejection", async () => {
	const state = liveSheet("Leave Application")
	state.context.sessionEmployee = { data: { name: "STAFF" } }
	state.context.computed = computed
	state.run(
		["WITHDRAWABLE_DOCTYPES", "isOwnDraft"]
			.map((name) => declaration(sheet, name))
			.join("\n")
	)
	const { parse: parseTemplate } = require("@vue/compiler-dom")
	const root = parseTemplate(source(sheet).split("<script setup>")[0])
	const expressions = []
	const walk = (node) => {
		for (const prop of node.props || [])
			if (prop.name === "if" && prop.exp?.content.includes("isOwnDraft"))
				expressions.push(prop.exp.content)
		for (const child of node.children || []) walk(child)
	}
	walk(root)
	assert.equal(expressions.length, 1)
	const ownBar = expressions[0]
		.replace(/\bisOwnDraft\b/g, "isOwnDraft.value")
		.replace(/\bworkflow\b/g, "workflow.value")
	assert.equal(state.run(ownBar), true)
	state.requests[0].resolve({
		actions: ["Rejected"],
		modified: state.context.document.doc.modified,
	})
	await tick()
	assert.equal(state.run(ownBar), false)
	assert.equal(state.run("hasPermission('reject')"), true)
	assert.equal(state.run("hasPermission('approve')"), false)
	state.stop()
})

test("approvable FormView never falls back to a raw Submit while its decision capability is unavailable", () => {
	for (const doctype of types) {
		for (const status of ["Open", "Draft", "Approved", "Rejected"]) {
			const context = vm.createContext({
				computed,
				props: {
					doctype,
					id: "REQUEST",
					isSubmittable: true,
					showFormButton: true,
				},
				isFormDirty: ref(false),
				formModel: ref({
					docstatus: 0,
					status,
					approval_status: status,
					employee: "STAFF",
				}),
				employee: { data: { name: "REVIEWER" } },
				hasPermission: () => true,
				REQUEST_SUMMARY_FIELDS: Object.fromEntries(types.map((dt) => [dt, []])),
			})
			vm.runInContext(
				["SUBMIT_REQUIRES_STATUS", "formButton"]
					.map((name) => declaration(form, name))
					.join("\n"),
				context
			)
			assert.equal(
				vm.runInContext("formButton.value", context),
				null,
				`${doctype}/${status}`
			)
		}
	}
})

test("legacy PWA Submit uses finalize with its reviewed revision for all six types", async () => {
	for (const doctype of types) {
		for (const status of ["Approved", "Rejected"]) {
			const state = liveSheet(doctype)
			state.context.document.doc[
				doctype === "Expense Claim" ? "approval_status" : "status"
			] = status
			state.context.document.originalDoc = JSON.parse(
				JSON.stringify(state.context.document.doc)
			)
			state.requests.at(-1).resolve({
				actions: ["Submit"],
				modified: state.context.document.doc.modified,
			})
			await tick()
			state.run("updateDocumentStatus({status: 'Approved'})")
			assert.equal(
				state.requests.filter((r) => r.options.url.endsWith(".decide")).length,
				0
			)
			state.run("updateDocumentStatus({docstatus: 1})")
			const call = state.requests.at(-1)
			assert.equal(call.options.url, "hrms.api.approval.finalize")
			assert.equal(call.options.params.docstatus, 1)
			assert.equal(call.options.params.expected_modified, "2026-09-08 12:00:00")
			state.run("updateDocumentStatus({docstatus: 1})")
			assert.equal(state.requests.at(-1), call)
			call.resolve({ docstatus: 1, status })
			await tick()
			assert.equal(state.successes.length, 1)
			state.stop()
		}
	}
})

test("PWA workflow keeps ownership even when plain decision authority exists", async () => {
	const state = liveSheet()
	state.requests[0].resolve({
		actions: ["Approved", "Rejected"],
		modified: state.context.document.doc.modified,
	})
	await tick()
	state.context.workflow.value = { hasWorkflow: true }
	assert.equal(state.run("hasPermission('approval')"), false)
	state.run("updateDocumentStatus({status: 'Approved'})")
	assert.equal(state.requests.length, 1)
	state.stop()
})

test("own draft workflow is reachable before Edit and Withdraw", async () => {
	const state = liveSheet("Leave Application")
	state.context.sessionEmployee = { data: { name: "STAFF" } }
	state.run(
		["WITHDRAWABLE_DOCTYPES", "isOwnDraft"]
			.map((name) => declaration(sheet, name))
			.join("\n")
	)
	const { parse: parseTemplate } = require("@vue/compiler-dom")
	const root = parseTemplate(source(sheet).split("<script setup>")[0])
	const branches = []
	const walk = (node) => {
		for (const prop of node.props || []) {
			if (
				["if", "else-if"].includes(prop.name) &&
				(prop.exp?.content.includes("isOwnDraft") ||
					node.tag === "WorkflowActionSheet")
			)
				branches.push({ tag: node.tag, expression: prop.exp.content })
		}
		for (const child of node.children || []) walk(child)
	}
	walk(root)
	const selected = () =>
		branches.find(({ expression }) =>
			state.run(
				expression
					.replace(/\bisOwnDraft\b/g, "isOwnDraft.value")
					.replace(/\bworkflow\b/g, "workflow.value")
			)
		)?.tag
	assert.equal(
		selected(),
		"div",
		"non-workflow draft recovery remains available"
	)
	state.context.workflow.value = { hasWorkflow: true }
	assert.equal(selected(), "WorkflowActionSheet")
	state.stop()
})

test("actual installed shared document resource refuses same-revision local edits immediately", async () => {
	const state = liveSheet("OT Request", true)
	state.requests[0].resolve({
		actions: ["Approved", "Rejected"],
		modified: state.context.document.doc.modified,
	})
	await tick()
	assert.equal(state.run("hasPermission('approval')"), true)
	const shared = state.run(
		"createDocumentResource({doctype: initial.doctype, name: initial.name, auto: false})"
	)
	assert.equal(
		shared,
		state.context.document,
		"actual installed cache shares the resource"
	)
	shared.doc.claimed_hours = 9
	assert.equal(shared.isDirty, false, "installed dirty watcher has not run yet")
	assert.equal(
		state.run("hasPermission('approval')"),
		false,
		"the same-tick dirty window is refused"
	)
	state.run("updateDocumentStatus({status: 'Approved'})")
	assert.equal(
		state.requests.filter((r) => r.options.url.endsWith(".decide")).length,
		0
	)
	await tick()
	assert.equal(shared.isDirty, true)
	assert.equal(state.run("hasPermission('approval')"), false)
	delete shared.doc.claimed_hours
	assert.equal(
		state.run("hasPermission('approval')"),
		false,
		"restoring clean data requires a fresh capability"
	)
	state.requests
		.at(-1)
		.resolve({
			actions: ["Approved", "Rejected"],
			modified: shared.doc.modified,
		})
	await tick()
	assert.equal(shared.isDirty, false)
	assert.equal(state.run("hasPermission('approval')"), true)
	state.stop()
})

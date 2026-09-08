import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import vm from "node:vm"

const source = readFileSync(
	new URL("../../hrms/public/js/utils/request_approval.js", import.meta.url),
	"utf8"
)
function desk(doctype = "OT Request") {
	const calls = [],
		confirms = [],
		buttons = new Map(),
		alerts = []
	const frm = {
		doctype,
		doc: { name: "OT-A", modified: "2026-09-08 12:00:00", docstatus: 0 },
		dirty: false,
		is_new: () => false,
		is_dirty: () => frm.dirty,
		page: {
			clear_primary_action() {
				buttons.delete("primary")
			},
			set_primary_action(label, click) {
				buttons.set("primary", { label, click })
			},
		},
		add_custom_button(label, click) {
			buttons.set(label, { label, click })
		},
		remove_custom_button(label) {
			buttons.delete(label)
		},
		reload_doc() {
			frm.reloads = (frm.reloads || 0) + 1
		},
	}
	const context = vm.createContext({
		hrms: { approval: {} },
		__: (text) => text,
		console: { debug() {} },
		frappe: {
			provide() {},
			model: { has_workflow: () => Boolean(frm.workflow) },
			ui: { form: { on() {} } },
			call(options) {
				calls.push(options)
			},
			confirm(text, callback) {
				confirms.push(callback)
			},
			show_alert(value) {
				alerts.push(value)
			},
		},
	})
	vm.runInContext(source, context)
	return { frm, calls, confirms, buttons, alerts, api: context.hrms.approval }
}
function respond(
	state,
	index,
	actions = ["Approved", "Rejected"],
	modified = "2026-09-08 12:00:00"
) {
	state.calls[index].callback({ message: { actions, modified } })
}
function authorize(state, actions) {
	state.api.add_buttons(state.frm)
	respond(state, state.calls.length - 1, actions)
}

test("dirty Desk forms keep Save and never request decision controls", () => {
	const state = desk()
	state.frm.dirty = true
	state.buttons.set("primary", { label: "Save" })
	state.api.add_buttons(state.frm)
	assert.equal(state.buttons.get("primary").label, "Save")
	assert.equal(state.calls.length, 0)
})

test("late capability responses cannot replace Save or target a different name/revision", () => {
	for (const mutate of [
		(s) => {
			s.frm.dirty = true
			s.buttons.set("primary", { label: "Save" })
		},
		(s) => {
			s.frm.doc.name = "OT-B"
		},
		(s) => {
			s.frm.doc.modified = "2026-09-08 12:01:00"
		},
	]) {
		const state = desk()
		state.api.add_buttons(state.frm)
		mutate(state)
		respond(state, 0)
		assert.notEqual(state.buttons.get("primary")?.label, "Approve")
		assert.equal(state.buttons.has("Reject"), false)
	}
})

test("newer capability denial cannot be overwritten by an older approval response", () => {
	const state = desk()
	state.api.add_buttons(state.frm)
	state.api.add_buttons(state.frm)
	respond(state, 1, [])
	respond(state, 0)
	assert.equal(state.buttons.size, 0)
})

test("Approve and Reject guard edits/navigation at click and confirmation time", () => {
	for (const action of ["primary", "Reject"]) {
		for (const phase of ["click", "confirm"]) {
			for (const mutate of [
				(s) => {
					s.frm.dirty = true
				},
				(s) => {
					s.frm.doc.name = "OT-B"
				},
				(s) => {
					s.frm.doc.modified = "2026-09-08 12:01:00"
				},
			]) {
				const state = desk()
				authorize(state)
				const button = state.buttons.get(action)
				if (phase === "click") mutate(state)
				button.click()
				if (phase === "confirm") mutate(state)
				state.confirms[0]?.()
				assert.equal(
					state.calls.filter((call) => call.method.endsWith(".decide")).length,
					0
				)
			}
		}
	}
})

test("a clean decision sends the reviewed server revision and does not double-submit", () => {
	const state = desk()
	authorize(state)
	state.buttons.get("primary").click()
	state.confirms[0]()
	state.confirms[0]()
	const decisions = state.calls.filter((call) =>
		call.method.endsWith(".decide")
	)
	assert.equal(decisions.length, 1)
	assert.equal(decisions[0].args.expected_modified, "2026-09-08 12:00:00")
	decisions[0].callback({ message: { docstatus: 1, status: "Approved" } })
	assert.equal(state.frm.reloads, 1)
})

const types = [
	"Leave Application",
	"Expense Claim",
	"Shift Request",
	"OT Request",
	"Attendance Request",
	"Replacement Leave Claim",
]
test("all six legacy decided drafts offer Submit with the displayed revision", () => {
	for (const doctype of types) {
		for (const status of ["Approved", "Rejected"]) {
			const state = desk(doctype)
			state.frm.doc[
				doctype === "Expense Claim" ? "approval_status" : "status"
			] = status
			authorize(state, ["Submit"])
			assert.equal(state.buttons.get("primary")?.label, "Submit")
			assert.equal(state.buttons.has("Reject"), false)
			state.buttons.get("primary").click()
			state.confirms[0]()
			const call = state.calls.at(-1)
			assert.equal(call.method, "hrms.api.approval.finalize")
			assert.equal(call.args.docstatus, 1)
			assert.equal(call.args.expected_modified, "2026-09-08 12:00:00")
		}
	}
})
test("own Leave's reject-only authority renders and dispatches only Reject", () => {
	const state = desk("Leave Application")
	authorize(state, ["Rejected"])
	assert.equal(state.buttons.has("primary"), false)
	assert.equal(state.buttons.get("Reject")?.label, "Reject")
	state.buttons.get("Reject").click()
	state.confirms[0]()
	assert.equal(state.calls.at(-1).args.status, "Rejected")
	state.api.decide(state.frm, "Approved")
	assert.equal(state.confirms.length, 1)
})
test("newer capability revision cannot authorize values the Desk has not displayed", () => {
	const state = desk()
	state.api.add_buttons(state.frm)
	respond(state, 0, ["Approved", "Rejected"], "2026-09-08 12:01:00")
	assert.equal(state.buttons.size, 0)
	assert.equal(state.frm.doc.modified, "2026-09-08 12:00:00")
	assert.equal(state.alerts.length, 1)
	state.api.decide(state.frm, "Approved")
	assert.equal(state.confirms.length, 0)
})
test("late decision completion cannot reload a different or edited Desk document", () => {
	for (const mutate of [
		(s) => {
			s.frm.dirty = true
		},
		(s) => {
			s.frm.doc.name = "OTHER"
		},
	]) {
		const state = desk()
		authorize(state)
		state.buttons.get("primary").click()
		state.confirms[0]()
		const call = state.calls.at(-1)
		mutate(state)
		call.callback({ message: { docstatus: 1 } })
		call.always()
		assert.equal(state.frm.reloads, undefined)
		assert.equal(state.frm._hrms_deciding, false)
	}
})

test("Desk workflow keeps its controls and bypasses plain decision capability", () => {
	const state = desk()
	state.frm.workflow = true
	state.buttons.set("primary", { label: "Workflow action" })
	state.api.add_buttons(state.frm)
	assert.equal(state.buttons.get("primary").label, "Workflow action")
	assert.equal(state.calls.length, 0)
})

test("clean saved draft without modified removes native Submit without requesting capability", () => {
	const state = desk()
	delete state.frm.doc.modified
	state.buttons.set("primary", { label: "Submit" })
	state.api.add_buttons(state.frm)
	assert.equal(state.buttons.has("primary"), false)
	assert.equal(state.calls.length, 0)
})

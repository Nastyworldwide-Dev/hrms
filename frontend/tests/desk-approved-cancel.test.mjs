// Hotfix 14 Sep 2026: Desk shows its native Cancel only with the cancel DocPerm,
// so a reports_to-only manager had no way to cancel an approved request there.
// hrms/public/js/utils/approved_request_cancel.js asks can_cancel_approved and
// adds a Cancel that goes through hrms.api.approval.finalize.
// Run: cd frontend && node --test tests/desk-approved-cancel.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import vm from "node:vm"

const source = readFileSync(
	new URL(
		"../../hrms/public/js/utils/approved_request_cancel.js",
		import.meta.url
	),
	"utf8"
)

function desk({
	docstatus = 1,
	nativeCancel = 0,
	doctype = "OT Request",
	roles = [],
} = {}) {
	const calls = [],
		confirms = [],
		buttons = new Map(),
		handlers = {}
	const frm = {
		doctype,
		doc: { name: "OT-A", modified: "2026-09-14 12:00:00", docstatus },
		perm: [{ read: 1, cancel: nativeCancel }],
		add_custom_button(label, click) {
			buttons.set(label, click)
		},
		reload_doc() {
			frm.reloads = (frm.reloads || 0) + 1
		},
	}
	const context = vm.createContext({
		hrms: {},
		__: (text) => text,
		console: { info() {}, debug() {} },
		frappe: {
			provide(path) {
				context.hrms[path.split(".")[1]] ||= {}
			},
			user: { has_role: (role) => roles.includes(role) },
			ui: {
				form: {
					on(doctype, events) {
						handlers[doctype] = events
					},
				},
			},
			call(options) {
				calls.push(options)
			},
			confirm(text, callback) {
				confirms.push(callback)
			},
		},
	})
	vm.runInContext(source, context)
	return { frm, calls, confirms, buttons, handlers }
}

test("every approved-request doctype runs the check on refresh", () => {
	const { handlers } = desk()
	assert.deepEqual(Object.keys(handlers).sort(), [
		"Attendance Request",
		"Compensatory Leave Request",
		"Employee Advance",
		"Expense Claim",
		"Leave Application",
		"OT Request",
		"Replacement Leave Claim",
		"Shift Request",
		"Travel Request",
	])
	for (const events of Object.values(handlers))
		assert.equal(typeof events.refresh, "function")
})

test("manager without native Cancel: server says yes -> Cancel calls finalize with docstatus 2", () => {
	const state = desk()
	state.handlers["OT Request"].refresh(state.frm)
	assert.equal(state.calls.length, 1)
	assert.equal(state.calls[0].method, "hrms.api.approval.can_cancel_approved")
	assert.deepEqual(
		{ ...state.calls[0].args },
		{ doctype: "OT Request", name: "OT-A" }
	)
	state.calls[0].callback({ message: { can_cancel: true, reason: null } })
	assert.ok(state.buttons.has("Cancel"))

	state.buttons.get("Cancel")()
	assert.equal(state.calls.length, 1, "nothing is sent before the confirm")
	state.confirms[0]()
	const cancel = state.calls[1]
	assert.equal(cancel.method, "hrms.api.approval.finalize")
	assert.equal(cancel.type, "POST")
	assert.deepEqual(
		{ ...cancel.args },
		{
			doctype: "OT Request",
			name: "OT-A",
			docstatus: 2,
			expected_modified: "2026-09-14 12:00:00",
		}
	)
	cancel.callback({ message: { docstatus: 2 } })
	assert.equal(state.frm.reloads, 1)
})

test("server says no -> no button", () => {
	const state = desk()
	state.handlers["OT Request"].refresh(state.frm)
	state.calls[0].callback({ message: { can_cancel: false, reason: "no" } })
	assert.equal(state.buttons.size, 0)
})

test("native Cancel present, or not submitted -> no check and no duplicate button", () => {
	for (const options of [
		{ nativeCancel: 1 },
		{ docstatus: 0 },
		{ docstatus: 2 },
	]) {
		const state = desk(options)
		state.handlers["OT Request"].refresh(state.frm)
		assert.equal(state.calls.length, 0, JSON.stringify(options))
		assert.equal(state.buttons.size, 0)
	}
})

test("a late answer for an older revision adds nothing", () => {
	const state = desk()
	state.handlers["OT Request"].refresh(state.frm)
	state.frm.doc = { ...state.frm.doc, modified: "2026-09-14 12:05:00" }
	state.calls[0].callback({ message: { can_cancel: true } })
	assert.equal(state.buttons.size, 0)
})

test("advances, travel requests and comp leave: HR gets the one plain Cancel check (no reason prompt)", () => {
	for (const doctype of [
		"Employee Advance",
		"Travel Request",
		"Compensatory Leave Request",
	]) {
		const { frm, calls, handlers } = desk({ doctype, roles: ["HR Manager"] })
		handlers[doctype].refresh(frm)
		assert.equal(calls.length, 1, `${doctype}: asks can_cancel_approved`)
		assert.equal(calls[0].method, "hrms.api.approval.can_cancel_approved")
	}
})

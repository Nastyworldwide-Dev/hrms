// What logout clears from the browser store. frappe-ui caches every document
// it loads under the key JSON(["<Doctype>", "<name>"]) — Profile's Employee
// record (name, date of birth, contacts) was still there after a real logout
// and a reload, readable by the next person on a shared phone (audit P0-5,
// SEC-STORE). Only keys this origin owns are cleared; nothing is wiped
// wholesale.
import { test } from "node:test"
import assert from "node:assert/strict"

globalThis.window = { location: { origin: "https://nadi.test" }, addEventListener() {} }
globalThis.document = { cookie: "", addEventListener() {}, documentElement: { style: {} } }
globalThis.localStorage = { getItem: () => null, setItem() {} }
globalThis.indexedDB = undefined
const { isClearedAtLogout } = await import("../personalCache.js")

const k = (...parts) => JSON.stringify(parts)

test("a document frappe-ui cached ([doctype, name]) is cleared at logout", () => {
	assert.equal(isClearedAtLogout(k("Employee", "HR-EMP-00001"), "a@x"), true)
	assert.equal(isClearedAtLogout(k("Leave Application", "HR-LAP-2026-00043"), "a@x"), true)
})

test("this user's private keys are cleared; another user's are left", () => {
	const origin = "https://nadi.test"
	assert.equal(isClearedAtLogout(k("hrms:private:v1", origin, "a@x", "hrms:shifts"), "a@x"), true)
	assert.equal(isClearedAtLogout(k("hrms:private:v1", origin, "b@x", "hrms:shifts"), "a@x"), false)
})

test("the old shared keys are cleared", () => {
	assert.equal(isClearedAtLogout(k("hrms:shifts"), null), true)
	assert.equal(isClearedAtLogout(k("nsty:hr-contacts"), null), true)
})

test("keys that are not ours, or not JSON arrays, are left alone", () => {
	assert.equal(isClearedAtLogout("not json", "a@x"), false)
	assert.equal(isClearedAtLogout(JSON.stringify({ a: 1 }), "a@x"), false)
	assert.equal(isClearedAtLogout(k("some-other-app", "x", "y"), "a@x"), false)
})

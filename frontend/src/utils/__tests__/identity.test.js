// The login-normalization the router guard compares with.
// Run with: yarn --cwd frontend test
import { test } from "node:test"
import assert from "node:assert/strict"

const identity = await import("../identity.js")
const { normalizeLogin } = identity

test("normalizeLogin trims and lowercases", () => {
	assert.equal(normalizeLogin("  Foo@Bar.com "), "foo@bar.com")
})

test("a case-drifted mirror user_id matches the normalized session user", () => {
	// The exact stranding this guards: the backend resolves a mirror employee
	// whose user_id was written unnormalized, and returns it raw. Both sides
	// through normalizeLogin must compare equal, or the guard bounces a valid
	// user to /invalid-employee.
	assert.equal(
		normalizeLogin("Identity_Staff@Example.com"),
		normalizeLogin("identity_staff@example.com")
	)
})

// The router guard's decision (main.js). It used to skip the employee check
// whenever the TARGET was /invalid-employee, so a valid employee who reached
// that URL — a stale tab, a bookmark, the runtime crawl of 15 Sep 2026 — was
// shown "Login failed / Employee not found" for an account that works.
test("employeeGate: a valid employee is let through, and sent Home from the failure page", () => {
	const { employeeGate } = identity
	assert.equal(typeof employeeGate, "function", "identity.js must export employeeGate")
	const employee = { user_id: "Staff@Example.com" }
	const user = { name: "staff@example.com" }
	assert.equal(employeeGate({ to: "Home", employee, user }), null)
	assert.deepEqual(employeeGate({ to: "InvalidEmployee", employee, user }), { name: "Home" })
	assert.deepEqual(employeeGate({ to: "Login", employee, user }), { name: "Home" })
})

test("employeeGate: no matching employee goes to the failure page, and stays there", () => {
	const { employeeGate } = identity
	const user = { name: "staff@example.com" }
	assert.deepEqual(employeeGate({ to: "Home", employee: null, user }), { name: "InvalidEmployee" })
	assert.deepEqual(
		employeeGate({ to: "Home", employee: { user_id: "other@example.com" }, user }),
		{ name: "InvalidEmployee" }
	)
	assert.equal(
		employeeGate({ to: "InvalidEmployee", employee: null, user }),
		null,
		"no redirect loop"
	)
})

test("non-strings normalize to empty, never throw", () => {
	assert.equal(normalizeLogin(null), "")
	assert.equal(normalizeLogin(undefined), "")
	assert.equal(normalizeLogin(123), "")
})

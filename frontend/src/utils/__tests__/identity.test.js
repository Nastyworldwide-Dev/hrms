// The login-normalization the router guard compares with.
// Run with: yarn --cwd frontend test
import { test } from "node:test"
import assert from "node:assert/strict"

const { normalizeLogin } = await import("../identity.js")

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

test("non-strings normalize to empty, never throw", () => {
	assert.equal(normalizeLogin(null), "")
	assert.equal(normalizeLogin(undefined), "")
	assert.equal(normalizeLogin(123), "")
})

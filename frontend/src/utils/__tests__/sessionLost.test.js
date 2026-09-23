// Only a server that says "you are not logged in" ends a session. Every
// route change re-reads the user; offline, that read fails with a network
// error, and the router treated ANY failure as logged out — changing page
// with no signal threw people onto Login, which reads "No login methods are
// available" when the login-method fetch also fails (audit P0-6).
import { test } from "node:test"
import assert from "node:assert/strict"

import { isSessionLost } from "../sessionLost.js"

test("a network failure (offline, timeout) does not end the session", () => {
	assert.equal(isSessionLost(new TypeError("Failed to fetch")), false)
	assert.equal(isSessionLost(new Error("NetworkError when attempting to fetch resource.")), false)
	assert.equal(isSessionLost(undefined), false)
})

test("the server saying 401 or 403 ends it", () => {
	assert.equal(isSessionLost(Object.assign(new Error("x"), { response: { status: 401 } })), true)
	assert.equal(isSessionLost(Object.assign(new Error("x"), { response: { status: 403 } })), true)
})

test("an AuthenticationError or a Guest session ends it", () => {
	assert.equal(
		isSessionLost(Object.assign(new Error("x"), { exc_type: "AuthenticationError" })),
		true
	)
	assert.equal(isSessionLost(Object.assign(new Error("x"), { exc_type: "SessionExpired" })), true)
})

test("a server error (500) does not end it", () => {
	assert.equal(isSessionLost(Object.assign(new Error("x"), { response: { status: 500 } })), false)
	assert.equal(
		isSessionLost(
			Object.assign(new Error("x"), { exc_type: "ValidationError", response: { status: 417 } })
		),
		false
	)
})

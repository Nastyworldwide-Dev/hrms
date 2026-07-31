// Regression tests for the login page's Forgot Password flow — the PWA login
// had no reset entry point at all, so locked-out staff were dead-ended.
// Run with: node --test frontend/tests/
import { test } from "node:test"
import assert from "node:assert/strict"

const { sendPasswordResetLink } = await import("../src/utils/resetPassword.js")

const mockFetcher = (status) => {
	const calls = []
	const fetcher = async (url, options) => {
		calls.push({ url, options })
		return { ok: status >= 200 && status < 300, status }
	}
	fetcher.calls = calls
	return fetcher
}

test("posts the email to frappe's guest reset_password endpoint", async () => {
	const fetcher = mockFetcher(200)
	await sendPasswordResetLink("jane@example.com", fetcher)

	assert.equal(fetcher.calls.length, 1)
	const { url, options } = fetcher.calls[0]
	assert.equal(url, "/api/method/frappe.core.doctype.user.user.reset_password")
	assert.equal(options.method, "POST")
	assert.deepEqual(JSON.parse(options.body), { user: "jane@example.com" })
})

test("404 (unknown user) surfaces an account-not-found message", async () => {
	await assert.rejects(
		() => sendPasswordResetLink("nobody@example.com", mockFetcher(404)),
		/No account found/
	)
})

test("429 (rate limited) surfaces a try-again-later message", async () => {
	await assert.rejects(
		() => sendPasswordResetLink("jane@example.com", mockFetcher(429)),
		/try again later/
	)
})

test("other server errors surface a generic failure", async () => {
	await assert.rejects(
		() => sendPasswordResetLink("jane@example.com", mockFetcher(500)),
		/Could not send/
	)
})

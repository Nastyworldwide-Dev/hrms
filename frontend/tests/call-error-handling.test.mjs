// Regression tests for frappe-ui's call() error path (patched via
// patches/frappe-ui+0.1.105.patch). The PWA showed '"undefined" is not valid
// JSON' instead of the server's real validation message whenever the error
// path hit an unguarded JSON.parse. Run with: node --test frontend/tests/
import { test } from "node:test"
import assert from "node:assert/strict"

globalThis.window = globalThis.window || { location: { hostname: "test.localhost" } }

const call = (await import("../node_modules/frappe-ui/src/utils/call.js")).default

const mockFetch = (status, body) => {
	globalThis.fetch = async () => ({
		ok: status >= 200 && status < 300,
		status,
		text: async () => body,
		json: async () => JSON.parse(body),
	})
}

test("417 with _server_messages surfaces the real validation message", async () => {
	const serverMessage = JSON.stringify({
		message: "Only Leave Applications with status 'Approved' and 'Rejected' can be submitted",
	})
	mockFetch(
		417,
		JSON.stringify({
			exc_type: "ValidationError",
			_server_messages: JSON.stringify([serverMessage]),
		})
	)

	await assert.rejects(
		() => call("frappe.client.set_value", {}),
		(e) => {
			assert.match(e.messages.join(" "), /status 'Approved' and 'Rejected'/)
			assert.equal(e.exc_type, "ValidationError")
			return true
		}
	)
})

test("malformed _server_messages does not raise SyntaxError, keeps a fallback message", async () => {
	mockFetch(
		417,
		JSON.stringify({
			exc_type: "ValidationError",
			_server_messages: "undefined",
		})
	)

	await assert.rejects(
		() => call("frappe.client.set_value", {}),
		(e) => {
			assert.notEqual(e.name, "SyntaxError")
			assert.ok(e.messages.length, "expected a fallback message")
			return true
		}
	)
})

test("non-JSON error body (gateway HTML page) rejects with a usable Error", async () => {
	mockFetch(502, "<html><body>502 Bad Gateway</body></html>")

	await assert.rejects(
		() => call("frappe.client.set_value", {}),
		(e) => {
			assert.notEqual(e.name, "SyntaxError")
			assert.notEqual(e.name, "TypeError")
			assert.equal(e.status, 502)
			assert.ok(e.messages.length, "expected a fallback message")
			return true
		}
	)
})

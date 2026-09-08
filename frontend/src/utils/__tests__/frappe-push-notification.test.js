// Push subscribe/unsubscribe are believed only when the server says success.
//
// Before (Astra's 360 audit, N06): the helper checked HTTP status alone. Frappe
// answers 200 with {message: {success, message}} and `success` is independent —
// the relay being down came back as 200 + success:false, the token was stored
// as enabled anyway, and every later attempt with the same token skipped
// registration. Disabling also dropped the token even when the server refused
// to unsubscribe, and its catch block referenced an undefined variable.
//
// Executes the vendored helper class inside a VM with fetch, storage,
// Notification and the firebase calls as seams. Run from frontend/:
//   node --test src/utils/__tests__/frappe-push-notification.test.js
import test from "node:test"
import assert from "node:assert/strict"
import vm from "node:vm"
import { readFileSync } from "node:fs"

const source = readFileSync(new URL("../frappe-push-notification.js", import.meta.url), "utf8")
	.replace(/^import\s+[\s\S]*?from\s+["'][^"']+["']\s*\n/gm, "")
	.replace(/export default /g, "")

function fixture({ subscribe, unsubscribe, storedToken = null }) {
	const store = new Map()
	if (storedToken) store.set("firebase_token_hrms", storedToken)
	const calls = []
	const context = vm.createContext({
		console: { warn() {}, error() {} },
		window: { frappe: { boot: { push_relay_server_url: "https://relay" } } },
		localStorage: {
			getItem: (k) => (store.has(k) ? store.get(k) : null),
			setItem: (k, v) => store.set(k, v),
			removeItem: (k) => store.delete(k),
		},
		Notification: { requestPermission: async () => "granted" },
		isSupported: async () => true,
		getToken: async () => "TOKEN-1",
		deleteToken: async () => {},
		initializeApp() {},
		getMessaging() {},
		onFCMMessage() {},
		fetch: async (url) => {
			const action = url.includes("unsubscribe") ? "unsubscribe" : "subscribe"
			calls.push(action)
			const reply = action === "subscribe" ? subscribe : unsubscribe
			return {
				status: reply.status ?? 200,
				json: async () => {
					if (reply.malformed) throw new SyntaxError("not json")
					return { message: reply.message }
				},
			}
		},
	})
	vm.runInContext(source, context)
	const sdk = vm.runInContext('new FrappePushNotification("hrms")', context)
	sdk.fetchVapidPublicKey = async () => "VAPID"
	sdk.messaging = {}
	return { sdk, store, calls }
}

test("HTTP 200 with success:false is a failed subscription: nothing is stored", async () => {
	const s = fixture({ subscribe: { message: { success: false, message: "relay unavailable" } } })
	await assert.rejects(() => s.sdk.enableNotification(), /Failed to subscribe/)
	assert.equal(s.store.has("firebase_token_hrms"), false)
	assert.equal(s.sdk.token, null)
})

test("a confirmed subscription is stored, and only then", async () => {
	const s = fixture({ subscribe: { message: { success: true, message: "ok" } } })
	const result = await s.sdk.enableNotification()
	assert.equal(result.permission_granted, true)
	assert.equal(s.store.get("firebase_token_hrms"), "TOKEN-1")
})

test("a malformed body or a non-200 status is a failure too", async () => {
	for (const reply of [{ malformed: true }, { status: 500 }]) {
		const s = fixture({ subscribe: reply })
		await assert.rejects(() => s.sdk.enableNotification(), /Failed to subscribe/)
		assert.equal(s.store.has("firebase_token_hrms"), false)
	}
})

test("after a failure the same token is registered again, not skipped", async () => {
	const s = fixture({ subscribe: { message: { success: false } } })
	await assert.rejects(() => s.sdk.enableNotification())
	s.calls.length = 0
	await assert.rejects(() => s.sdk.enableNotification())
	assert.deepEqual(s.calls, ["subscribe"], "nothing was stored, so the retry really subscribes")
})

test("a refused unsubscribe keeps the token and reports the failure", async () => {
	const s = fixture({ unsubscribe: { message: { success: false, message: "relay unavailable" } }, storedToken: "TOKEN-1" })
	await assert.rejects(() => s.sdk.disableNotification(), /Could not unsubscribe/)
	assert.equal(s.store.get("firebase_token_hrms"), "TOKEN-1")
	assert.equal(s.sdk.isNotificationEnabled(), true)
})

test("a confirmed unsubscribe clears the token", async () => {
	const s = fixture({ unsubscribe: { message: { success: true } }, storedToken: "TOKEN-1" })
	await s.sdk.disableNotification()
	assert.equal(s.store.has("firebase_token_hrms"), false)
	assert.equal(s.sdk.isNotificationEnabled(), false)
})

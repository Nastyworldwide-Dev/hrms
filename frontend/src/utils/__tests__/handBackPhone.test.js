// Logging out hands the phone back (auth hunt AU-1, 5 Oct 2026). Logout never told the push relay to
// stop sending this phone the leaving person's notifications, and the token stayed in localStorage.
// The next person to sign in on a shared phone found the same token, skipped subscribing, and the
// first person's approvals and overtime pushes kept arriving.
import { test } from "node:test"
import assert from "node:assert/strict"
import { handBackPhone } from "../handBackPhone.js"

// skipped subscribing, and the first person's approvals and overtime pushes kept arriving.
test("a failed unsubscribe never stops anyone from logging out", async () => {
	const calls = []
	const failing = {
		disableNotification: async () => {
			calls.push("try")
			throw new Error("relay down")
		},
	}
	await handBackPhone(failing)
	assert.deepEqual(calls, ["try"])
})

test("a relay that never answers cannot hold the logout past the wait", async () => {
	const hanging = { disableNotification: () => new Promise(() => {}) }
	const outcome = await Promise.race([
		handBackPhone(hanging, 30).then(() => "went ahead"),
		new Promise((resolve) => setTimeout(() => resolve("still waiting"), 600)),
	])
	assert.equal(outcome, "went ahead")
})

test("with push never enabled there is nothing to hand back", async () => {
	await handBackPhone(undefined)
	await handBackPhone({})
})

test("a failed unsubscribe still forgets the token on THIS phone, so the next person subscribes fresh", async () => {
	const store = new Map([["firebase_token_hrms", "tokenA"]])
	const storage = { removeItem: (k) => store.delete(k) }
	await handBackPhone(
		{
			disableNotification: async () => {
				throw new Error("relay down")
			},
			projectName: "hrms",
			token: "tokenA",
		},
		50,
		storage
	)
	assert.equal(store.has("firebase_token_hrms"), false)
})

// registerAppWorker (moved out of main.js, alpha.41 S12): the app's one worker address, the push
// settings that last worked, and the two moves for phones installed before alpha.12. Executes the
// real module with the browser's seams faked: navigator.serviceWorker, localStorage, window.
// Imports the real swRegistration.js, which needs `vue` (installed) and nothing else. The address
// rule for stored push settings (sorted keys, last good copy) is workerURL.test.js's; a launch with
// settings would start the real Firebase SDK, so these cases run without any.
import { test, beforeEach, afterEach } from "node:test"
import assert from "node:assert/strict"

import { registerAppWorker } from "../serviceWorker.js"
import { swRegistration } from "../../data/swRegistration.js"

const had = {}
const KEYS = ["window", "navigator", "localStorage", "Notification", "document"]
let registered, store, unregistered

function install({ relay = false, oldScopes = [] } = {}) {
	registered = []
	unregistered = []
	store = new Map()
	const registration = {
		scope: "https://x.test/hrms/",
		update: async () => {},
		addEventListener() {},
	}
	// navigator is a getter on newer Node: define, never assign
	const put = (key, value) =>
		Object.defineProperty(globalThis, key, { value, configurable: true, writable: true })
	put("localStorage", {
		getItem: (k) => store.get(k) ?? null,
		setItem: (k, v) => store.set(k, v),
	})
	put("document", { visibilityState: "visible", addEventListener() {} })
	put("navigator", {
		serviceWorker: {
			register: async (url, options) => (registered.push({ url, options }), registration),
			getRegistrations: async () =>
				oldScopes.map((scope) => ({
					scope: `https://x.test${scope}`,
					unregister: async () => unregistered.push(scope),
				})),
		},
	})
	put("window", { frappe: { boot: relay ? { push_relay_server_url: "https://relay.test" } : {} } })
}

const settle = () => new Promise((resolve) => setTimeout(resolve, 20))

beforeEach(() => {
	for (const key of KEYS) had[key] = Object.getOwnPropertyDescriptor(globalThis, key)
})
afterEach(() => {
	for (const key of KEYS) {
		if (had[key]) Object.defineProperty(globalThis, key, had[key])
		else delete globalThis[key]
	}
})

test("with no relay and nothing stored the worker registers at its plain address, scoped to /hrms", async () => {
	install()
	await registerAppWorker()
	await settle()
	assert.deepEqual(registered, [
		{ url: "/hrms/sw.js", options: { type: "classic", scope: "/hrms" } },
	])
	assert.ok(swRegistration.value, "the registration is handed to data/swRegistration.js")
})

test("a pre-alpha.12 worker is retired once the app-root worker registers, and only that one", async () => {
	install({ oldScopes: ["/assets/hrms/frontend/", "/hrms/"] })
	await registerAppWorker()
	await settle()
	assert.deepEqual(unregistered, ["/assets/hrms/frontend/"])
})

test("a browser without service workers is one console error, not a throw", async () => {
	install()
	delete globalThis.navigator.serviceWorker
	const errors = []
	const real = console.error
	console.error = (...args) => errors.push(args.join(" "))
	try {
		await registerAppWorker()
	} finally {
		console.error = real
	}
	assert.deepEqual(errors, ["Service worker not enabled/supported by the browser"])
	assert.deepEqual(registered, [])
})

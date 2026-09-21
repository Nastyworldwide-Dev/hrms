// A-H1 (21 Sep 2026 approval-lifecycle audit): socket.js capped reconnects at
// 5 and nobody listened for reconnect_failed, so ~20 s of bad signal killed
// every realtime feature for the page's lifetime. Executes the real socket.js
// wiring with a captured `io`, then proves the captured options against the
// REAL socket.io-client manager on a dead port: it must still be trying after
// the old cap of 5.
// Run: cd frontend && node --experimental-test-module-mocks --test tests/socket-reconnect-forever.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import vm from "node:vm"
import { io } from "socket.io-client"

const source = readFileSync(
	new URL("../src/socket.js", import.meta.url),
	"utf8"
)
const executable = source
	.replace(/^import\s+[\s\S]*?from\s+["'][^"']+["']\s*\n/gm, "")
	.replace(/export (const|function)/g, "$1")

function boot({ connected = false } = {}) {
	const calls = { io: [], connect: 0, managerHandlers: {}, docHandlers: {} }
	const socket = {
		connected,
		on() {},
		connect: () => (calls.connect += 1),
		io: { on: (event, fn) => (calls.managerHandlers[event] = fn) },
	}
	const context = vm.createContext({
		console: { info() {} },
		window: {
			location: { hostname: "example.invalid", port: "" },
			site_name: "site",
		},
		document: {
			visibilityState: "hidden",
			addEventListener: (event, fn) => (calls.docHandlers[event] = fn),
		},
		io: (url, options) => {
			calls.io.push({ url, options })
			return socket
		},
		getCachedResource: () => null,
		getCachedListResource: () => null,
		personalCacheKey: (k) => k,
	})
	vm.runInContext(`${executable}\ninitSocket()`, context)
	return { calls, socket, document: context.document }
}

test("the client never stops reconnecting: no attempt cap, a 30 s backoff ceiling", () => {
	const { calls } = boot()
	const [{ options }] = calls.io
	assert.equal(
		options.reconnectionAttempts,
		undefined,
		"the old cap of 5 is gone"
	)
	assert.equal(options.reconnectionDelayMax, 30000)
	assert.equal(options.withCredentials, true)
})

test("after 6 failed attempts the real manager is still trying with these options", async () => {
	const { calls } = boot()
	const [{ options }] = calls.io
	const socket = io("http://127.0.0.1:1/site", {
		...options,
		reconnectionDelay: 5,
		reconnectionDelayMax: 10,
		randomizationFactor: 0,
		timeout: 200,
		transports: ["websocket"],
	})
	const attempts = await new Promise((resolve, reject) => {
		let n = 0
		socket.io.on("reconnect_attempt", () => {
			n += 1
			if (n >= 6) resolve(n)
		})
		socket.io.on("reconnect_failed", () =>
			reject(new Error(`gave up after ${n} attempts`))
		)
		setTimeout(
			() => reject(new Error(`only ${n} attempts in 8 s`)),
			8000
		).unref()
	}).finally(() => socket.close())
	assert.ok(attempts >= 6)
})

test("coming back to the foreground with the socket down starts a connection", () => {
	const { calls, document } = boot({ connected: false })
	document.visibilityState = "visible"
	calls.docHandlers.visibilitychange()
	assert.equal(calls.connect, 1)
})

test("a live socket is left alone on foreground; reconnect_failed also reconnects", () => {
	const { calls, socket, document } = boot({ connected: true })
	document.visibilityState = "visible"
	calls.docHandlers.visibilitychange()
	assert.equal(calls.connect, 0)
	socket.connected = false
	calls.managerHandlers.reconnect_failed()
	assert.equal(calls.connect, 1)
})

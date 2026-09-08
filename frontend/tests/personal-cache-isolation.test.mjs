import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync, existsSync } from "node:fs"
import { fileURLToPath } from "node:url"
import vm from "node:vm"

const root = new URL("../", import.meta.url)
const source = (file) => readFileSync(new URL(file, root), "utf8")
const executable = (text) => text
	.replace(/^import\s+[\s\S]*?from\s+["'][^"']+["']\s*\n/gm, "")
	.replace(/^export\s*\{[^}]+\}\s*$/gm, "")
	.replace(/export (const|function|async function)/g, "$1")
const tick = () => new Promise((resolve) => setImmediate(resolve))

// Execute the installed persistence + resource implementations and application
// declarations. Only browser storage/HTTP/Vue identity wrappers are simulated.
function browser(user, store, origin = "https://example.invalid", sessionStorage = new Map()) {
	const requests = []
	const config = {}
	const events = {}
	let reloads = 0
	const request = (options) => new Promise((resolve, reject) => requests.push({ options, resolve, reject }))
	const context = vm.createContext({
		console: { info() {}, warn() {} }, Event, URLSearchParams,
		document: { cookie: `user_id=${encodeURIComponent(user)}`, documentElement: { style: {} }, addEventListener: (event, callback) => { events[event] = callback } },
		window: { location: { origin, reload() { reloads++ }, replace() {} }, addEventListener: (event, callback) => { events[event] = callback } }, indexedDB: {},
		localStorage: { getItem: (key) => sessionStorage.get(key) ?? null, setItem: (key, value) => sessionStorage.set(key, value) },
		crypto: { randomUUID: () => String(sessionStorage.size) + Math.random() },
		get: async (key) => store.get(key),
		set: async (key, value) => store.set(key, value),
		del: async (key) => store.delete(key),
		keys: async () => [...store.keys()],
		delMany: async (keys) => keys.forEach((key) => store.delete(key)),
		reactive: (value) => value, computed: (fn) => ({ get value() { return fn() } }),
		getConfig: (key) => config[key], setConfig: (key, value) => { config[key] = value },
		request, frappeRequest: request, makeLoudRequest: (fetcher) => fetcher,
		employeeResource: { data: { name: user }, reset() {} },
		userResource: { data: { name: user }, reset() {} },
		router: { replace() {} },
	})
	vm.runInContext(executable(source("node_modules/frappe-ui/src/resources/local.js")), context)
	vm.runInContext(executable(source("node_modules/frappe-ui/src/resources/resources.js")), context)
	vm.runInContext(executable(source("node_modules/frappe-ui/src/resources/listResource.js")), context)
	const helper = new URL("src/utils/personalCache.js", root)
	if (existsSync(fileURLToPath(helper))) vm.runInContext(executable(readFileSync(helper, "utf8")), context)
	vm.runInContext(executable(source("src/resourceConfig.js")), context)
	vm.runInContext(executable(source("src/data/overtime.js")), context)
	vm.runInContext(executable(source("src/data/notifications.js")), context)
	return { context, requests, events, get reloads() { return reloads }, run: (code) => vm.runInContext(code, context) }
}

test("OT and notification cache stays available to its account but never another account/site", async () => {
	const store = new Map()
	const a = browser("account-a@example.invalid", store)
	const ot = a.requests.find(({ options }) => options.url === "hrms.api.get_ot_requests")
	ot.resolve([{ name: "OT-A", employee: "account-a@example.invalid", ot_date: null }])
	await tick()
	const notificationFetch = a.run("notifications.list.fetch()")
	a.requests.find(({ options }) => options.params?.doctype === "PWA Notification").resolve([
		{ name: "NOTICE-A", message: "Account A private message", to_user: "account-a@example.invalid" },
	])
	await notificationFetch
	await tick()
	const sameAccount = browser("account-a@example.invalid", store)
	await tick()
	assert.equal(sameAccount.run("myOTRequests.data[0].name"), "OT-A")
	assert.equal(sameAccount.run("notifications.data[0].name"), "NOTICE-A")
	for (const [user, origin] of [
		["account-b@example.invalid", "https://example.invalid"],
		["Guest", "https://example.invalid"],
		["account-a@example.invalid", "https://other.invalid"],
	]) {
		const next = browser(user, store, origin)
		await tick()
		assert.equal(next.run("myOTRequests.params.employee"), user)
		assert.equal(next.run("myOTRequests.data"), null, `OT privacy for ${user} at ${origin}`)
		assert.equal(next.run("notifications.data"), null, `notification privacy for ${user} at ${origin}`)
	}
})

test("startup removes legacy personal keys while logout removes only the departing identity", async () => {
	const origin = "https://example.invalid"
	const key = (user) => JSON.stringify(["hrms:private:v1", origin, user, "hrms:my_ot_requests"])
	const aKey = key("account-a@example.invalid")
	const bKey = key("account-b@example.invalid")
	const store = new Map([
		[JSON.stringify(["hrms:my_ot_requests"]), "[]"],
		[JSON.stringify(["nsty:remote-checkin-pending"]), "[]"],
		[aKey, "[]"], [bKey, "[]"],
		[JSON.stringify(["other-app:preferences"]), "untouched"],
	])
	const a = browser("account-a@example.invalid", store)
	await tick()
	assert.equal(store.has(JSON.stringify(["hrms:my_ot_requests"])), false, "remove legacy shared OT cache")
	assert.equal(store.has(JSON.stringify(["nsty:remote-checkin-pending"])), false, "remove legacy remote cache")
	assert.equal(store.has(aKey), true, "startup preserves this account's scoped cache")
	a.run(executable(source("src/data/session.js")))
	const logout = a.run("session.logout.fetch()")
	a.context.document.cookie = "user_id=Guest"
	a.requests.find(({ options }) => options.url === "logout").resolve({})
	await logout
	await tick()
	assert.equal(a.run("session.user"), null)
	assert.equal(store.has(aKey), false, "logout clears departing identity")
	assert.equal(store.has(bKey), true, "logout preserves another identity's scoped data")
	assert.equal(store.get(JSON.stringify(["other-app:preferences"])), "untouched")
	// A request already on the wire may settle after logout. Its writes must
	// remain under A's scoped key, never repopulate the forbidden shared key.
	a.requests.find(({ options }) => options.url === "hrms.api.get_ot_requests")
		.resolve([{ name: "OT-LATE-A", employee: "account-a@example.invalid", ot_date: null }])
	await tick()
	assert.equal(store.has(JSON.stringify(["hrms:my_ot_requests"])), false)
	const b = browser("account-b@example.invalid", store)
	await tick()
	assert.equal(b.run("myOTRequests.data.length"), 0)
})

test("server realtime cache names refresh the current account's scoped resource", async () => {
	const b = browser("account-b@example.invalid", new Map())
	const handlers = {}
	b.context.io = () => ({ on: (event, handler) => { handlers[event] = handler } })
	b.run(executable(source("src/socket.js")))
	b.run("initSocket()")
	const before = b.requests.length
	handlers["hrms:refetch_resource"]({ cache_key: "hrms:my_ot_requests" })
	assert.equal(b.requests.length, before + 1)
	assert.equal(b.requests.at(-1).options.params.employee, "account-b@example.invalid")
})

test("identity isolation property holds for account pairs including encoded cookie characters", async () => {
	const users = ["a@example.invalid", "A@example.invalid", "name+tag@example.invalid", "name&team@example.invalid"]
	const store = new Map()
	for (const user of users) {
		const current = browser(user, store)
		current.requests.find(({ options }) => options.url === "hrms.api.get_ot_requests")
			.resolve([{ name: `OT-${user}`, employee: user, ot_date: null }])
		await tick()
	}
	for (const user of users) {
		const current = browser(user, store)
		await tick()
		assert.equal(current.run("myOTRequests.data[0].employee"), user)
		assert.equal(current.run("myOTRequests.params.employee"), user)
	}
})

test("a surviving A tab cannot fetch or cache B data after another tab changes the login", async () => {
	const store = new Map()
	const a = browser("account-a@example.invalid", store)
	await a.run("clearPersonalCaches('account-a@example.invalid')")
	a.context.document.cookie = "user_id=account-b%40example.invalid"
	const before = a.requests.length
	a.run("myOTRequests.reload()")
	await tick()
	assert.equal(a.requests.length, before, "stale resource must not dispatch with B's cookie")
	assert.equal(a.reloads, 1, "stale tab starts a new page lifetime")
	assert.equal(a.context.document.documentElement.style.visibility, "hidden")
	assert.equal(a.run("personalCacheKey('hrms:my_issues')"), null, "late-created resources cannot adopt B's identity")
})

test("identity changes during a request prevent both resource and list completion persistence", async () => {
	const store = new Map()
	const a = browser("account-a@example.invalid", store)
	a.run("notifications.list.fetch()")
	a.context.document.cookie = "user_id=account-b%40example.invalid"
	a.requests.find(({ options }) => options.url === "hrms.api.get_ot_requests")
		.resolve([{ name: "OT-B", employee: "account-b@example.invalid", ot_date: null }])
	a.requests.find(({ options }) => options.params?.doctype === "PWA Notification")
		.resolve([{ name: "NOTICE-B", message: "B private message" }])
	await tick()
	assert.equal(a.run("myOTRequests.data"), null, "stale fulfilled OT response must be discarded")
	assert.equal(a.run("notifications.data"), null, "list's uncached inner fetch must also be guarded")
	const freshA = browser("account-a@example.invalid", store)
	await tick()
	assert.equal(freshA.run("myOTRequests.data"), null)
	assert.equal(freshA.run("notifications.data"), null)
})

test("a new login epoch discards old completions even when the final cookie user is unchanged", async () => {
	const store = new Map()
	const storage = new Map()
	const old = browser("account-a@example.invalid", store, "https://example.invalid", storage)
	const loginTab = browser("account-a@example.invalid", store, "https://example.invalid", storage)
	loginTab.context.call = async () => ({ message: "Logged In" })
	loginTab.run(executable(source("src/data/session.js")))
	await loginTab.run("session.login('account-a@example.invalid', 'synthetic-password')")
	old.events.storage({ key: "hrms:session-epoch" })
	assert.equal(old.reloads, 1)
	old.requests.find(({ options }) => options.url === "hrms.api.get_ot_requests")
		.resolve([{ name: "OLD-EPOCH", employee: "account-a@example.invalid", ot_date: null }])
	await tick()
	assert.equal(old.run("myOTRequests.data"), null)
	assert.equal(store.has(JSON.stringify(["hrms:private:v1", "https://example.invalid", "account-a@example.invalid", "hrms:my_ot_requests"])), false)
})

test("focus/visibility hide stale data, and old rejected requests cannot mutate the resource", async () => {
	for (const event of ["focus", "visibilitychange"]) {
		const a = browser("account-a@example.invalid", new Map())
		a.events[event]()
		assert.equal(a.reloads, 0)
		a.context.document.cookie = "user_id=account-b%40example.invalid"
		a.events[event]()
		assert.equal(a.reloads, 1)
		a.requests.find(({ options }) => options.url === "hrms.api.get_ot_requests")
			.reject(new Error("Synthetic old-session failure"))
		await tick()
		assert.equal(a.run("myOTRequests.error"), null)
		assert.equal(a.context.document.documentElement.style.visibility, "hidden")
	}
})

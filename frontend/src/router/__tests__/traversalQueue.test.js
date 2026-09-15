// A navigation started while a Back/Forward (history traversal) is still in
// its guards CANCELS that traversal. vue-router accepts the cancel and leaves
// the browser history where the traversal put it; @ionic/vue-router cannot:
// its afterEach returns early on a failure without clearing the pending pop
// info, so the NEXT navigation is animated as a "back" — the previous page is
// left painted while the route and URL say the new one (e.g. /support), and
// the new page never renders.
//
// queueBehindTraversal holds push/replace until the traversal has settled.
import { test } from "node:test"
import assert from "node:assert/strict"

import { queueBehindTraversal } from "../traversalQueue.js"

// The boundary: vue-router's router + its RouterHistory. afterEach/onError
// handlers and history listeners are driven by the test, the way the real
// router drives them.
function fakeRouter() {
	const listeners = []
	const after = []
	const errors = []
	const calls = []
	const router = {
		options: { history: { listen: (cb) => (listeners.push(cb), () => {}) } },
		afterEach: (fn) => after.push(fn),
		onError: (fn) => errors.push(fn),
		push: (to) => (calls.push(["push", to]), Promise.resolve()),
		replace: (to) => (calls.push(["replace", to]), Promise.resolve()),
		resolve: (to) => ({ fullPath: typeof to === "string" ? to : to.path }),
	}
	return {
		router,
		calls,
		traverse: (to) => listeners.forEach((cb) => cb(to, "/prev", { type: "pop", delta: -1 })),
		afterEach: (to, failure) => after.forEach((fn) => fn({ fullPath: to }, {}, failure)),
		error: (err, to) => errors.forEach((fn) => fn(err, { fullPath: to })),
	}
}

const flush = () => new Promise((resolve) => setImmediate(resolve))

// The app's first navigation has landed: from here vue-router follows popstate.
function boot(f) {
	queueBehindTraversal(f.router)
	f.afterEach("/home")
}

test("with no traversal in flight, push and replace go straight through", async () => {
	const f = fakeRouter()
	boot(f)
	await f.router.push("/support")
	await f.router.replace({ path: "/home" })
	assert.deepEqual(f.calls, [
		["push", "/support"],
		["replace", { path: "/home" }],
	])
})

test("a push during a Back waits until the Back has landed, then runs", async () => {
	const f = fakeRouter()
	boot(f)
	f.traverse("/home") // Back pressed: guards still running
	const pushed = f.router.push("/support")
	await flush()
	assert.deepEqual(f.calls, [], "must not cancel the in-flight Back")
	f.afterEach("/home") // Back confirmed
	await pushed
	assert.deepEqual(f.calls, [["push", "/support"]])
})

test("an unrelated navigation settling does not release the queue early", async () => {
	const f = fakeRouter()
	boot(f)
	f.traverse("/home")
	const pushed = f.router.push("/support")
	f.afterEach("/dashboard/kpi", { type: 8 }) // an older push, cancelled by the Back
	await flush()
	assert.deepEqual(f.calls, [])
	f.afterEach("/home")
	await pushed
	assert.deepEqual(f.calls, [["push", "/support"]])
})

test("a Back whose guard redirects or aborts still releases the queue", async () => {
	const f = fakeRouter()
	boot(f)
	f.traverse("/home")
	const pushed = f.router.push("/support")
	f.afterEach("/login") // guard redirected elsewhere: any successful landing settles it
	await pushed
	assert.deepEqual(f.calls, [["push", "/support"]])

	f.traverse("/home")
	const replaced = f.router.replace("/more")
	f.afterEach("/home", { type: 4 }) // aborted by next(false)
	await replaced
	assert.deepEqual(f.calls.at(-1), ["replace", "/more"])
})

test("a Back that throws in a guard releases the queue", async () => {
	const f = fakeRouter()
	boot(f)
	f.traverse("/home")
	const pushed = f.router.push("/support")
	f.error(new Error("chunk failed"), "/home")
	await pushed
	assert.deepEqual(f.calls, [["push", "/support"]])
})

test("queued navigations keep their order and return the router's result", async () => {
	const f = fakeRouter()
	f.router.push = (to) => (f.calls.push(["push", to]), Promise.resolve(`done ${to}`))
	boot(f)
	f.traverse("/home")
	const a = f.router.push("/a")
	const b = f.router.push("/b")
	f.afterEach("/home")
	assert.equal(await a, "done /a")
	assert.equal(await b, "done /b")
	assert.deepEqual(f.calls, [
		["push", "/a"],
		["push", "/b"],
	])
})

test("a second Back before the first lands waits for the latest one", async () => {
	const f = fakeRouter()
	boot(f)
	f.traverse("/kpi")
	f.traverse("/home") // pressed twice: vue-router follows the latest
	const pushed = f.router.push("/support")
	f.afterEach("/kpi", { type: 8 }) // the first traversal, cancelled by the second
	await flush()
	assert.deepEqual(f.calls, [])
	f.afterEach("/home")
	await pushed
	assert.deepEqual(f.calls, [["push", "/support"]])
})

test("a Back whose guard redirect is itself aborted still releases the queue", async () => {
	const f = fakeRouter()
	boot(f)
	f.traverse("/home")
	f.router.push("/support")
	f.afterEach("/login", { type: 4 }) // redirected, then the redirect aborted by next(false)
	await flush()
	assert.deepEqual(f.calls, [["push", "/support"]], "a held push must never wait forever")
})

test("a popstate before the first navigation has landed holds nothing", async () => {
	// vue-router only follows popstate once its first navigation lands; before
	// that no afterEach would ever release a hold.
	const f = fakeRouter()
	queueBehindTraversal(f.router)
	f.traverse("/home")
	f.router.push("/support")
	await flush()
	assert.deepEqual(f.calls, [["push", "/support"]])
})

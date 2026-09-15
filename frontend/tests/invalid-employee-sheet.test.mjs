// The "Login failed" sheet belongs to /invalid-employee and nowhere else
// (runtime crawl, 15 Sep 2026).
//
// Two defects on one page:
//   1. The sheet is an ion-modal, presented at the app root rather than inside
//      the page, so leaving the route left it open on top of every later page.
//      Closing it the obvious way was not safe either: its did-dismiss handler
//      logged the user out, so a close-on-leave would have signed people out
//      for navigating.
//   2. It told VALID employees "Employee not found". The server's identity
//      status answers reason "ok" for them, and the page never read the
//      reason — it only showed the message, which falls back to "not found".
//
// Executes the component's real <script setup> inside a VM, the way the
// TicketNew recovery test does. Run from frontend/:
//   node --test tests/invalid-employee-sheet.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import vm from "node:vm"
import { readFileSync } from "node:fs"
import { computed, ref, effectScope } from "vue"

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8")
const script = (path) => read(path).split("<script setup>")[1].split("</script>")[0]
const executable = (text) =>
	text.replace(/^import\s+[\s\S]*?from\s+["'][^"']+["']\s*\n/gm, "").replace(/export /g, "")

function fixture() {
	const logouts = []
	const navigations = []
	const leaveHooks = []
	let identityOptions = null
	const scope = effectScope()
	const context = vm.createContext({
		computed,
		ref,
		console: { info() {}, warn() {} },
		inject: (key) =>
			key === "$session"
				? { user: "staff@example.com", logout: { submit: () => logouts.push("logout") } }
				: (text) => text,
		createResource: (options) => {
			identityOptions = options
			return { data: null }
		},
		onIonViewWillLeave: (hook) => leaveHooks.push(hook),
		useRouter: () => ({ replace: (to) => navigations.push(to) }),
	})
	const run = (code) => vm.runInContext(code, context)
	scope.run(() => run(executable(script("../src/views/InvalidEmployee.vue"))))
	return { run, logouts, navigations, leaveHooks, identity: () => identityOptions, stop: () => scope.stop() }
}

test("leaving the page closes the sheet and does not sign the user out", () => {
	const s = fixture()
	assert.equal(s.run("showDialog.value"), true)
	assert.equal(s.leaveHooks.length, 1, "the page must close its sheet on leave")
	s.leaveHooks[0]()
	assert.equal(s.run("showDialog.value"), false, "the sheet is closed before the next page shows")
	s.run("onDismissed()") // ion-modal's did-dismiss fires after the programmatic close
	assert.deepEqual(s.logouts, [], "navigating away is not a request to sign out")
	s.stop()
})

test("dismissing the sheet on the page still signs the user out", () => {
	const s = fixture()
	s.run("onDismissed()")
	assert.deepEqual(s.logouts, ["logout"])
	s.stop()
})

test("a valid employee who lands here is sent Home, never shown 'not found'", () => {
	const s = fixture()
	s.identity().onSuccess({ reason: "ok", message: "", user: "staff@example.com" })
	// built inside the VM, so compare plain structure, not that realm's prototypes
	assert.deepEqual(JSON.parse(JSON.stringify(s.navigations)), [{ name: "Home" }])
	assert.equal(s.run("showDialog.value"), false)
	s.run("onDismissed()")
	assert.deepEqual(s.logouts, [], "being routed Home is not a sign-out")
	s.stop()
})

test("a real denial keeps the sheet and its reason", () => {
	const s = fixture()
	s.identity().onSuccess({ reason: "no_employee", message: "Your account is not linked" })
	assert.deepEqual(s.navigations, [])
	assert.equal(s.run("showDialog.value"), true)
	s.stop()
})

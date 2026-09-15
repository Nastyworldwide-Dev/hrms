// /helpdesk/new obeys the same availability gate as the Helpdesk hub
// (runtime crawl, 15 Sep 2026).
//
// The hub hides the IT pill on a site without the Helpdesk app, but the
// new-ticket route stayed reachable by URL: it fetched get_options
// unconditionally, the server answered DoesNotExistError "Helpdesk is not
// installed on this site", and the employee got a raw "Could not load" toast,
// an unhandled rejection, and a form that could never submit.
//
// Now: probe answered false → a friendly "not set up here" state with Back;
// probe not answered yet → loading; answered true → the form, and only then
// the options fetch. Executes the real <script setup> in a VM
// (ticket-new-recovery recipe). Run from frontend/:
//   node --test tests/ticket-new-availability.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import vm from "node:vm"
import { readFileSync } from "node:fs"
import { computed, reactive, ref, watch, effectScope, nextTick } from "vue"

const source = readFileSync(new URL("../src/views/helpdesk/TicketNew.vue", import.meta.url), "utf8")
const script = source.split("<script setup>")[1].split("</script>")[0]
const template = source.split("<script setup>")[0]
const executable = (text) =>
	text
		.replace(/^import\s+[\s\S]*?from\s+["'][^"']+["']\s*\n/gm, "")
		.replace(/export /g, "")

function fixture(available) {
	const optionFetches = []
	const helpdeskAvailable = reactive({ data: available, error: null, loading: false })
	const scope = effectScope()
	const context = vm.createContext({
		computed,
		reactive,
		ref,
		watch,
		console: { info() {}, warn() {} },
		FileAttachment: class {},
		newTicket: { loading: false, submit: () => Promise.resolve({ name: "HD-1" }) },
		myTickets: { reload() {} },
		ticketOptions: { data: null, loading: false, fetch: () => optionFetches.push("fetch") },
		helpdeskAvailable,
		goBackOrHome: () => {},
		useRouter: () => ({ replace() {} }),
		inject: () => (s) => s,
	})
	const run = (code) => vm.runInContext(code, context)
	scope.run(() => run(executable(script)))
	return { run, optionFetches, helpdeskAvailable, stop: () => scope.stop() }
}

test("a site without Helpdesk shows the unavailable state and never asks for options", () => {
	const s = fixture(false)
	assert.equal(s.run("availability.value"), "no")
	assert.deepEqual(s.optionFetches, [], "get_options on a site without Helpdesk is the crawl's error")
	s.stop()
})

test("while the probe is unanswered the page waits, then loads options once it says yes", async () => {
	const s = fixture(null)
	assert.equal(s.run("availability.value"), "pending")
	assert.deepEqual(s.optionFetches, [])
	s.helpdeskAvailable.data = true
	await nextTick()
	assert.equal(s.run("availability.value"), "yes")
	assert.deepEqual(s.optionFetches, ["fetch"])
	s.stop()
})

test("a site with Helpdesk loads the options straight away", () => {
	const s = fixture(true)
	assert.equal(s.run("availability.value"), "yes")
	assert.deepEqual(s.optionFetches, ["fetch"])
	s.stop()
})

test("the template gates the form on the answer and gives the unavailable state a way back", () => {
	assert.match(template, /v-if="availability === 'no'"/, "an unavailable branch")
	assert.match(template, /IT Helpdesk isn’t set up here/)
	assert.match(template, /v-else-if="availability === 'pending'"/, "a waiting branch")
	assert.match(template, /<form[^>]*v-else/, "the form renders only once the probe said yes")
	const unavailable = template.split(/v-if="availability === 'no'"/)[1].split("v-else-if")[0]
	assert.match(unavailable, /@click="goBack"|goBackOrHome/, "the unavailable state has its own Back")
})

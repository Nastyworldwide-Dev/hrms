// The Helpdesk create screen keeps a raised ticket and retries only what failed.
//
// Before (Astra's 360 audit): submit awaited Promise.allSettled for the
// attachments and navigated away regardless, so a failed upload lost the
// selected-file retry path — the detail page has no upload control — and a
// second Submit would have raised a second ticket. Leaving a half-typed new
// ticket also asked nothing. (PWA recovery row.)
//
// Executes the component's real <script setup> declarations inside a VM, the
// way the calendar and OT form tests do. Run from frontend/:
//   node --test tests/ticket-new-recovery.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import vm from "node:vm"
import { readFileSync } from "node:fs"
import { computed, reactive, ref, effectScope, nextTick } from "vue"

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8")
const script = (path) => read(path).split("<script setup>")[1].split("</script>")[0]
const executable = (text) =>
	text
		.replace(/^import\s+[\s\S]*?from\s+["'][^"']+["']\s*\n/gm, "")
		.replace(/export default /g, "")
		.replace(/export /g, "")
// Values built inside the VM carry that realm's Array/Object prototypes, which
// strict deepEqual rejects; compare plain structure instead.
const plain = (value) => JSON.parse(JSON.stringify(value))
const tick = async () => {
	await nextTick()
	await Promise.resolve()
	await Promise.resolve()
}

function fixture({ failing = [] } = {}) {
	const created = []
	const uploads = []
	const navigations = []
	const scope = effectScope()
	class FileAttachment {
		constructor(file) {
			this.file = file
		}
		upload(doctype, name) {
			uploads.push({ file: this.file.name, doctype, name })
			return failing.includes(this.file.name)
				? Promise.reject({ messages: ["too large"] })
				: Promise.resolve({ file_url: `/files/${this.file.name}` })
		}
	}
	const context = vm.createContext({
		computed,
		reactive,
		ref,
		console: { info() {}, warn() {} },
		FileAttachment,
		newTicket: {
			loading: false,
			submit: (payload) => {
				created.push(payload)
				return Promise.resolve({ name: `HD-TICKET-${created.length}` })
			},
		},
		myTickets: { reload() {} },
		ticketOptions: { data: null, fetch() {} },
		goBackOrHome: () => navigations.push("home"),
		useRouter: () => ({ replace: (to) => navigations.push(to) }),
		inject: () => (s, args = []) => s.replace(/\{(\d+)\}/g, (_, i) => args[i]),
	})
	const run = (code) => vm.runInContext(code, context)
	scope.run(() => run(executable(script("../src/views/helpdesk/TicketNew.vue"))))
	return { run, created, uploads, navigations, stop: () => scope.stop() }
}

test("a failed upload keeps the raised ticket and the retry re-sends only that file", async () => {
	const s = fixture({ failing: ["b.png"] })
	s.run("form.subject = 'Cannot sign in'; form.description = 'since Monday'")
	s.run("files.value = [{ name: 'a.png' }, { name: 'b.png' }]")
	await s.run("submit()")
	await tick()
	assert.equal(s.created.length, 1)
	assert.equal(s.run("ticketName.value"), "HD-TICKET-1")
	assert.deepEqual(plain(s.run("failedFiles.value.map((f) => f.name)")), ["b.png"])
	assert.deepEqual(plain(s.run("files.value.map((f) => f.name)")), ["b.png"], "only the failure stays selected")
	assert.equal(s.navigations.length, 0, "no navigation while a file is unattached")
	await s.run("submit()") // Retry uploads
	await tick()
	assert.equal(s.created.length, 1, "never a second ticket")
	assert.deepEqual(
		plain(s.uploads.map((u) => u.file)),
		["a.png", "b.png", "b.png"],
		"the retry re-sent only the failed file"
	)
	s.stop()
})

test("a clean submit raises once, attaches, and lands on the ticket", async () => {
	const s = fixture()
	s.run("form.subject = 'Printer'; form.description = 'jammed'; files.value = [{ name: 'a.png' }]")
	await s.run("submit()")
	await tick()
	assert.equal(s.created.length, 1)
	assert.deepEqual(plain(s.navigations), [{ name: "HelpdeskTicketDetail", params: { id: "HD-TICKET-1" } }])
	s.stop()
})

test("back on a dirty new ticket asks first; a pristine one just leaves", async () => {
	const s = fixture()
	s.run("goBack()")
	assert.deepEqual(s.navigations, ["home"])
	s.run("form.subject = 'x'")
	s.run("goBack()")
	assert.equal(s.run("showDiscardDialog.value"), true)
	assert.equal(s.navigations.length, 1, "nothing left the page yet")
	s.run("discardAndLeave()")
	assert.deepEqual(s.navigations, ["home", "home"])
	s.stop()
})

test("back after the ticket exists lands on that ticket, not on Home", async () => {
	const s = fixture({ failing: ["a.png"] })
	s.run("form.subject = 'x'; form.description = 'y'; files.value = [{ name: 'a.png' }]")
	await s.run("submit()")
	await tick()
	s.run("goBack()")
	assert.deepEqual(plain(s.navigations.at(-1)), { name: "HelpdeskTicketDetail", params: { id: "HD-TICKET-1" } })
	s.stop()
})

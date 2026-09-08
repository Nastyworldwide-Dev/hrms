// The attendance calendar owns one request per month and refreshes itself.
//
// Before: one resource re-fetched with new params on every month step, so a
// slow September response finishing after the user had stepped to October
// painted September's rows under October's title; nothing reloaded the month
// when the hourly job created an Attendance, and the error state offered no
// retry. (Astra's 360 audit, CAL-REFRESH.)
//
// Executes the component's real <script setup> declarations inside a VM with
// the installed frappe-ui resource implementation, the way the OT form test
// does. Run from frontend/: node --test tests/attendance-calendar-refresh.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import vm from "node:vm"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"
import { computed, ref, reactive, effectScope, nextTick } from "vue"

const require = createRequire(import.meta.url)
const dayjs = require("dayjs")
const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8")
const script = (path) => read(path).split("<script setup>")[1].split("</script>")[0]
const executable = (text) =>
	text
		.replace(/^import\s+[\s\S]*?from\s+["'][^"']+["']\s*\n/gm, "")
		.replace(/export default /g, "")
		.replace(/export /g, "")
const tick = async () => {
	await nextTick()
	await Promise.resolve()
	await Promise.resolve()
}

function fixture() {
	const calls = []
	const listeners = []
	const scope = effectScope()
	const context = vm.createContext({
		computed,
		ref,
		reactive,
		Event,
		console: { info() {}, warn() {} },
		getConfig: () => undefined,
		saveLocal: () => {},
		request: (options) => new Promise((resolve, reject) => calls.push({ options, resolve, reject })),
		personalCacheKey: () => null,
		useListUpdate: (socket, doctype, callback) => listeners.push({ doctype, callback }),
		defineExpose: () => {},
		inject: (key) =>
			key === "$dayjs"
				? dayjs
				: key === "$translate"
				? (s, args = []) => s.replace(/\{(\d+)\}/g, (_, i) => args[i])
				: { on() {}, off() {}, emit() {} },
	})
	vm.runInContext(executable(read("../node_modules/frappe-ui/src/resources/resources.js")), context)
	const run = (code) => vm.runInContext(code, context)
	scope.run(() => run(executable(script("../src/components/AttendanceCalendar.vue"))))
	run("firstOfMonth.value = dayjs('2026-09-01')")
	// The template reads calendarEvents on every render; a VM has no template,
	// so the fixture reads it wherever a render would.
	const render = () => run("calendarEvents.value")
	render()
	return {
		calls,
		listeners,
		run,
		requests: () => calls.map((c) => c.options.params.from_date),
		data: () => run("calendarEvents.value.data"),
		step: (months) => {
			run(`firstOfMonth.value = firstOfMonth.value.add(${months}, 'M')`)
			render()
		},
		stop: () => scope.stop(),
	}
}

test("a late response for the previous month never paints under the current one", async () => {
	const s = fixture()
	await tick()
	assert.deepEqual(s.requests(), ["2026-09-01"])
	s.step(1)
	await tick()
	assert.deepEqual(s.requests(), ["2026-09-01", "2026-10-01"])
	s.calls[0].resolve({ "2026-09-02": "Present" }) // September answers late
	await tick()
	assert.equal(s.data(), null, "October must not show September's rows")
	s.calls[1].resolve({ "2026-10-06": "Absent" })
	await tick()
	assert.deepEqual(s.data(), { "2026-10-06": "Absent" })
	s.step(-1)
	await tick()
	assert.deepEqual(s.data(), { "2026-09-02": "Present" }, "a fetched month shows at once")
	assert.equal(s.calls.length, 2, "stepping back does not refetch a month it already holds")
	s.stop()
})

test("an Attendance change reloads the month on show", async () => {
	const s = fixture()
	await tick()
	s.calls[0].resolve({ "2026-09-02": "Present" })
	await tick()
	assert.equal(s.listeners[0].doctype, "Attendance")
	s.listeners[0].callback("HR-ATT-00001")
	await tick()
	assert.deepEqual(s.requests(), ["2026-09-01", "2026-09-01"])
	s.calls[1].resolve({ "2026-09-02": "Present", "2026-09-07": "Present" })
	await tick()
	assert.equal(s.run("summary.value.Present"), 2)
	s.stop()
})

test("refresh reloads the shown month, which is what view re-entry and Try again call", async () => {
	const s = fixture()
	await tick()
	s.calls[0].reject(new Error("offline"))
	await tick()
	assert.ok(s.run("calendarEvents.value.error"))
	s.run("refresh()")
	await tick()
	assert.equal(s.calls.length, 2)
	s.calls[1].resolve({ "2026-09-03": "Half Day" })
	await tick()
	assert.equal(s.run("calendarEvents.value.error"), null)
	assert.equal(s.run("summary.value['Half Day']"), 1)
	s.stop()
})

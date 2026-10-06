// Pull down on Calendar (6 Oct 2026, alpha.36): the pull closed while the month's days were still
// loading, because Dashboard.refresh() started the calendar's reload without waiting for it. The
// refresher must stay open until the month, the dots and the shifts have ALL answered.
// Compiles the real Dashboard.vue setup (HelpdeskHub.test.js recipe); the calendar, the two
// resources and the Ionic hook are the boundaries.
import assert from "node:assert/strict"
import { test } from "node:test"
import { readFileSync } from "node:fs"
import { compileScript, parse } from "@vue/compiler-sfc"
import { defineAsyncComponent, ref } from "vue"

const read = (file) => readFileSync(new URL(file, import.meta.url), "utf8")
const dashboard = read("../attendance/Dashboard.vue")
const script = compileScript(parse(dashboard).descriptor, { id: "attendance-dashboard" })
const code = script.content
	.replace(/import[\s\S]*?from ["'][^"']+["'];?/g, "")
	.replace("export default", "return")

const deferred = () => {
	let resolve
	const promise = new Promise((r) => (resolve = r))
	return { promise, resolve }
}
const tick = () => new Promise((r) => setTimeout(r, 0))

function screen({ calendarRefresh }) {
	const calendar = ref(null)
	const bindings = {
		ref: (value) => (value === null ? calendar : ref(value)),
		defineAsyncComponent,
		onIonViewWillEnter() {},
		createResource: () => ({ reload: () => Promise.resolve() }),
		personalCacheKey: (key) => key,
		useRouter: () => ({}),
		monthFlags: { reload: () => Promise.resolve() },
		console: { info() {}, warn() {}, error() {} },
	}
	for (const name of Object.keys(script.imports)) if (!(name in bindings)) bindings[name] = {}
	const component = new Function(...Object.keys(bindings), code)(...Object.values(bindings))
	const vm = component.setup({}, { expose() {} })
	calendar.value = { refresh: calendarRefresh }
	return vm
}

test("the pull is not completed before the calendar's reload has resolved", async () => {
	const month = deferred()
	const vm = screen({ calendarRefresh: () => month.promise })
	let completed = 0
	const done = vm.refresh({ target: { complete: () => completed++ } })
	await tick()
	assert.equal(completed, 0, "the month is still loading, so the refresher stays open")
	month.resolve()
	await done
	assert.equal(completed, 1, "closed once, after the month answered")
})

test("a calendar whose reload fails still lets the pull close", async () => {
	// AttendanceCalendar.refresh() catches its own failure and resolves; a stub that rejects
	// anyway must not leave the refresher spinning (allSettled, not all).
	const vm = screen({ calendarRefresh: () => Promise.reject(new Error("offline")) })
	let completed = 0
	await vm.refresh({ target: { complete: () => completed++ } })
	assert.equal(completed, 1)
})

test("AttendanceCalendar.refresh() hands back the reload so a caller can wait for it", () => {
	const cal = read("../../components/AttendanceCalendar.vue")
	const start = cal.indexOf("function refresh() {")
	assert.notEqual(start, -1, "a refresh()")
	const body = cal.slice(start, cal.indexOf("\n}\n", start))
	assert.match(body, /return calendarEvents\.value\s*\.reload\(\)/, "the promise is returned")
	assert.match(body, /\.catch\?\.\(\(\) => console\.warn\("\[AttendanceCalendar\] refresh failed", key\)\)/, "a failure still logs and resolves")
	assert.match(cal, /useListUpdate\(socket, "Attendance", refresh\)/, "the socket callback is unchanged (ignores the return)")
})

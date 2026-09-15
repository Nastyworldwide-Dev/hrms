// The merged Helpdesk page: the pill switch renders the right list, the URL
// states the pill, memory reopens it, and the IT pill obeys the availability
// gate. Compiles the real SFC setup (CheckInPanel.location.test.js recipe);
// route, router, storage and the availability resource are the boundaries.
import assert from "node:assert/strict"
import { test } from "node:test"
import { readFileSync } from "node:fs"
import { compileScript, parse } from "@vue/compiler-sfc"
import { computed, nextTick, reactive, ref, watch } from "vue"

import * as hub from "../../../utils/helpdeskHub.js"

const source = readFileSync(new URL("../HelpdeskHub.vue", import.meta.url), "utf8")
const script = compileScript(parse(source).descriptor, { id: "helpdesk-hub" })
const code = script.content
	.replace(/import[\s\S]*?from ["'][^"']+["'];?/g, "")
	.replace("export default", "return")

function page({ query = {}, stored = null, available = true } = {}) {
	const route = reactive({ name: hub.HUB_ROUTE_NAME, query })
	const replaced = []
	const router = {
		replace: (to) => {
			replaced.push(to)
			route.query = { ...to.query }
		},
	}
	const storage = new Map(stored === null ? [] : [[hub.TAB_STORAGE_KEY, stored]])
	const helpdeskAvailable = reactive({ data: available })
	const mounted = []
	const bindings = {
		...hub,
		computed,
		inject: () => (text) => text,
		onMounted: (fn) => mounted.push(fn),
		ref,
		watch,
		useRoute: () => route,
		useRouter: () => router,
		helpdeskAvailable,
		localStorage: {
			getItem: (key) => storage.get(key) ?? null,
			setItem: (key, value) => storage.set(key, value),
		},
		console: { info() {}, warn() {}, error() {} },
	}
	for (const name of Object.keys(script.imports)) if (!(name in bindings)) bindings[name] = {}
	const component = new Function(...Object.keys(bindings), code)(...Object.values(bindings))
	const vm = component.setup({}, { expose() {} })
	return {
		vm,
		route,
		replaced,
		storage,
		helpdeskAvailable,
		mount: () => mounted.forEach((fn) => fn()),
	}
}

test("the template swaps the two EXISTING lists on the pill", () => {
	const template = parse(source).descriptor.template.content
	assert.match(template, /<IssuesTab v-if="tab === HR_TAB" \/>/)
	assert.match(template, /<HelpdeskList v-else \/>/)
	assert.match(template, /<GSegmented[\s\S]*?@update:modelValue="selectTab"/)
	assert.match(template, /pageTitle="__\('Helpdesk'\)"/)
	// a single-option segment renders nothing, so its row must not leave a spacer
	assert.match(template, /v-if="tabButtons\.length > 1"[\s\S]*?<GSegmented/)
})

test("opens on HR Issues by default, with both pills offered", () => {
	const { vm, mount, replaced } = page()
	assert.equal(vm.tab.value, "hr")
	assert.deepEqual(
		vm.tabButtons.value.map((b) => [b.key, b.label]),
		[
			["hr", "HR Issues"],
			["it", "IT Helpdesk"],
		]
	)
	mount()
	assert.deepEqual(
		replaced,
		[{ query: { tab: "hr" } }],
		"a bare URL is rewritten to state the pill"
	)
})

test("a deep link ?tab=it opens IT Helpdesk and nothing is rewritten", () => {
	const { vm, mount, replaced } = page({ query: { tab: "it" } })
	assert.equal(vm.tab.value, "it")
	mount()
	assert.deepEqual(replaced, [])
})

test("a bare visit reopens the remembered pill", () => {
	const { vm } = page({ stored: "it" })
	assert.equal(vm.tab.value, "it")
})

test("switching the pill renders the other list, remembers it and replaces the query", () => {
	const { vm, replaced, storage } = page({ query: { tab: "hr" } })
	vm.selectTab("it")
	assert.equal(vm.tab.value, "it")
	assert.equal(storage.get(hub.TAB_STORAGE_KEY), "it")
	assert.deepEqual(
		replaced,
		[{ query: { tab: "it" } }],
		"replace, never push — BACK leaves the page"
	)
})

test("BACK to the previous query restores that pill", async () => {
	const { vm, route } = page({ query: { tab: "hr" } })
	vm.selectTab("it")
	await nextTick() // the replace has landed
	route.query = { tab: "hr" } // history.back() lands on the earlier entry
	await nextTick()
	assert.equal(vm.tab.value, "hr")
})

test("a same-path navigation with junk in the query falls back to memory", async () => {
	const { vm, route, replaced } = page({ query: { tab: "hr" }, stored: "it" })
	assert.equal(vm.tab.value, "hr", "the URL wins while it is valid")
	route.query = { tab: "tickets" }
	await nextTick()
	assert.equal(vm.tab.value, "it")
	assert.deepEqual(replaced.at(-1), { query: { tab: "it" } })
})

test("without the Helpdesk app the IT pill is absent and ?tab=it clamps to HR Issues", () => {
	const { vm } = page({ query: { tab: "it" }, available: false })
	assert.equal(vm.tab.value, "hr")
	assert.deepEqual(
		vm.tabButtons.value.map((b) => b.key),
		["hr"]
	)
})

test("a cold ?tab=it survives the availability probe still being unanswered", async () => {
	// frappe-ui hydrates the cache asynchronously: data is null at setup
	const { vm, mount, replaced, helpdeskAvailable } = page({
		query: { tab: "it" },
		available: null,
	})
	assert.equal(vm.tab.value, "it", "not-yet-answered is not a refusal")
	assert.deepEqual(
		vm.tabButtons.value.map((b) => b.key),
		["hr", "it"]
	)
	mount()
	assert.deepEqual(replaced, [], "the URL keeps the pill the link asked for")
	helpdeskAvailable.data = true
	await nextTick()
	assert.equal(vm.tab.value, "it")
	assert.deepEqual(replaced, [])
})

test("the probe answering no after a cold ?tab=it clamps to HR Issues", async () => {
	const { vm, route, helpdeskAvailable } = page({ query: { tab: "it" }, available: null })
	helpdeskAvailable.data = false
	await nextTick()
	assert.equal(vm.tab.value, "hr")
	assert.equal(route.query.tab, "hr")
	assert.deepEqual(
		vm.tabButtons.value.map((b) => b.key),
		["hr"]
	)
})

test("availability answering late clamps a remembered IT pill back to HR Issues", async () => {
	const { vm, helpdeskAvailable, storage } = page({ stored: "it", available: true })
	assert.equal(vm.tab.value, "it")
	helpdeskAvailable.data = false
	await nextTick()
	assert.equal(vm.tab.value, "hr")
	assert.equal(storage.get(hub.TAB_STORAGE_KEY), "hr")
})

test("the tab ref is declared before every watch that reads it (KPI TDZ lesson)", () => {
	const setup = script.content
	const declared = setup.indexOf("const tab = ref(")
	const firstWatch = setup.indexOf("watch(")
	assert.ok(declared > -1 && firstWatch > -1)
	assert.ok(declared < firstWatch, "a watch above the ref it reads throws at setup")
})

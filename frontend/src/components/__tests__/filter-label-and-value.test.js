// Ticket "the list filters still offer the STORED pending word" (21 Sep 2026): rows say "Waiting",
// but the Status filter on Time off and Shift changes offered "Open" and "Draft". The filter must SHOW
// the words the rows show and still SEND the stored value (the DB, Desk views and reports read
// "Open" / "Draft"; changing them would be a data migration).
//
// Everything here is the real code, executed: FormField, GSelect and ListFiltersActionSheet are
// compiled and rendered (compileScript + SSR, the failed-load-says-so recipe); the two list files'
// setup runs for their real FILTER_CONFIG; ListView's setup runs so the payload is the one it builds.
// The boundaries are the network (createResource records what would be sent), the translator and the
// router. The status the person picks is read from the rendered <option>, so label and value are
// whatever the screen really offers.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { compileScript, parse } from "@vue/compiler-sfc"
import * as Vue from "vue"
import * as SSR from "vue/server-renderer"

import { filterCondition } from "../../utils/listFilters.js"
import { requestStatus } from "../../utils/requestStatus.js"
import { sentenceCase } from "../../utils/sentenceCase.js"
import { plainLabel } from "../../utils/plainLabel.js"
import { readValue } from "../../utils/readValue.js"

const read = (p) => readFileSync(new URL(p, import.meta.url), "utf8")
const stripImports = (text) =>
	text.replace(/^import[\s\S]*?from ["'][^"']+["'];?$/gm, "").replace("export default", "return")

// every helper the compiled templates alias (`import { x as _x } from "vue"`)
const aliases = Object.fromEntries(
	[...Object.entries(Vue), ...Object.entries(SSR)].map(([name, fn]) => [`_${name}`, fn])
)

function sfc(path, scope, { inline = true } = {}) {
	const { descriptor } = parse(read(path))
	const script = compileScript(descriptor, {
		id: path,
		inlineTemplate: inline,
		templateOptions: { ssr: true, ssrCssVars: [] },
	})
	const bindings = { ...aliases, ...scope }
	return new Function(...Object.keys(bindings), stripImports(script.content))(
		...Object.values(bindings)
	)
}

// A script-setup file that has no template of its own: run its setup() and hand back what it returns.
// Names it imports only for its template are stubs, so an unbound GButton cannot stop the setup.
function setupOf(path, props, scope) {
	const { descriptor } = parse(read(path))
	const script = compileScript(descriptor, { id: path })
	const stub = () => ({})
	const proxy = new Proxy(scope, {
		has: (_, key) => typeof key === "string",
		get: (target, key) =>
			typeof key === "symbol"
				? undefined
				: key in target
				? target[key]
				: key in globalThis
				? globalThis[key]
				: stub,
	})
	const body = `with (scope) { ${stripImports(script.content)} }`
	const component = new Function("scope", body)(proxy)
	return component.setup(props, { expose() {}, emit() {} })
}

const stubComponent = (tag) => ({ render: () => Vue.h(tag) })
const translateWith = (words) => (text) => words[text] ?? text

const FormField = sfc("../FormField.vue", {
	...Vue,
	GSelect: sfc("../glass/GSelect.vue", { ChevronsUpDown: stubComponent("i") }),
	GTextarea: stubComponent("textarea"),
	GInput: stubComponent("input"),
	GDatePicker: stubComponent("input"),
	GDateTimePicker: stubComponent("input"),
	GSwitch: stubComponent("input"),
	Link: stubComponent("div"),
	plainValue: readValue,
	sentenceCase,
	plainLabel,
})
const Sheet = sfc("../ListFiltersActionSheet.vue", { ...Vue, FormField })

async function render(component, props, translate = (t) => t) {
	const app = Vue.createSSRApp({ render: () => Vue.h(component, props) })
	app.provide("$translate", translate)
	app.config.globalProperties.__ = translate
	app.provide("$dayjs", () => ({ format: () => "" }))
	app.directive("value-row", { getSSRProps: () => ({}) })
	return SSR.renderToString(app)
}

// [{ label, value }] of the first <select> in the markup, the empty "All" row left out
function offered(html) {
	const select = html.match(/<select[\s\S]*?<\/select>/)[0]
	return [...select.matchAll(/<option([^>]*)>([^<]*)<\/option>/g)]
		.map(([, attrs, label]) => ({ label, value: attrs.match(/value="([^"]*)"/)?.[1] }))
		.filter((o) => o.value !== "")
}

const sheetHtml = (filterConfig, translate) =>
	render(
		Sheet,
		{
			filterConfig,
			filters: Vue.reactive(
				Object.fromEntries(filterConfig.map((f) => [f.fieldname, { value: null }]))
			),
		},
		translate
	)

const LISTS = [
	{ file: "../../views/leave/List.vue", doctype: "Leave Application", stored: "Open" },
	{
		file: "../../views/attendance/ShiftRequestList.vue",
		doctype: "Shift Request",
		stored: "Draft",
	},
]

const filterConfigOf = (file) =>
	setupOf(file, {}, { inject: () => (t) => t, requestStatus }).FILTER_CONFIG

// ListView's own setup, with the network recorded: the payload is what get() would be sent.
function listView(doctype, filterConfig) {
	const sent = []
	const returned = setupOf(
		"../ListView.vue",
		{ doctype, fields: ["name"], filterConfig, pageTitle: "x", orderBy: "creation desc" },
		{
			...Vue,
			filterCondition,
			createResource: () => ({ data: null, params: {}, submit: (params) => sent.push(params) }),
			debounce: (fn) => fn,
			modalController: { dismiss() {} },
			initialListTab: () => null,
			useRoute: () => ({ query: {} }),
			useRouter: () => ({ hasRoute: () => true }),
			inject: (key) =>
				({
					$translate: (t) => t,
					$employee: { data: { name: "HR-EMP-1" } },
					$dayjs: () => ({ tz: () => ({ format: () => "2026-10-07" }) }),
					$socket: {},
				}[key]),
			console,
		}
	)
	return { returned, sent }
}

for (const { file, doctype, stored } of LISTS) {
	test(`${doctype}: the status filter shows Waiting and still sends ${stored}`, async () => {
		const status = filterConfigOf(file).find((f) => f.fieldname === "status")
		const choices = offered(await sheetHtml([status]))
		assert.deepEqual(choices, [
			{ label: "Waiting", value: stored },
			{ label: "Approved", value: "Approved" },
			{ label: "Rejected", value: "Rejected" },
		])
		assert.ok(!choices.some((c) => c.label === stored), `the stored word ${stored} is never shown`)
	})

	test(`${doctype}: the list request carries ${stored}, not the shown word`, async () => {
		const config = filterConfigOf(file)
		const status = config.find((f) => f.fieldname === "status")
		const picked = offered(await sheetHtml([status])).find((c) => c.label === "Waiting")
		const { returned, sent } = listView(doctype, config)
		returned.filterMap.status.value = picked.value
		returned.applyFilters()
		const filters = sent.at(-1).filters
		// copied out of the vm sandbox: bun's deepEqual refuses arrays from another realm
		assert.deepEqual(JSON.parse(JSON.stringify(filters.filter((f) => f[1] === "status"))), [
			[doctype, "status", "=", stored],
		])
		assert.ok(!JSON.stringify(filters).includes("Waiting"), "the label never reaches the server")
	})

	test(`${doctype}: every status word the filter shows is the word a row with that value shows`, async () => {
		const status = filterConfigOf(file).find((f) => f.fieldname === "status")
		for (const { label, value } of offered(await sheetHtml([status]))) {
			// a waiting row is a draft (docstatus 0); a decided one is submitted (docstatus 1)
			const row = { status: value, docstatus: value === stored ? 0 : 1 }
			assert.equal(requestStatus(doctype, row).label, label, `${value}: filter vs row chip`)
		}
		// and `stored` really is this doctype's pending word: a submitted row carrying it reads Approved
		assert.equal(requestStatus(doctype, { status: stored, docstatus: 1 }).label, "Approved")
	})
}

test("labels go through the translator; values never do", async () => {
	const status = filterConfigOf(LISTS[0].file).find((f) => f.fieldname === "status")
	const choices = offered(
		await sheetHtml([status], translateWith({ Waiting: "Menunggu", Open: "Terbuka" }))
	)
	assert.deepEqual(choices[0], { label: "Menunggu", value: "Open" })
})

test("a plain list of words works as before: the word is both label and value", async () => {
	const words = (options) => [{ fieldname: "kind", fieldtype: "Select", label: "Kind", options }]
	const expected = [
		{ label: "Draft", value: "Draft" },
		{ label: "Paid", value: "Paid" },
	]
	assert.deepEqual(offered(await sheetHtml(words(["Draft", "Paid"]))), expected, "array of words")
	assert.deepEqual(
		offered(await sheetHtml(words("Draft\nPaid"))),
		expected,
		"one per line, as Frappe stores them"
	)
	assert.deepEqual(
		offered(await sheetHtml(words(["Draft", "Paid"]), translateWith({ Paid: "Dibayar" }))),
		[expected[0], { label: "Dibayar", value: "Paid" }],
		"a word's label is translated, its value is not"
	)
})

test("a pair with no label falls back to its value", async () => {
	const config = [
		{
			fieldname: "kind",
			fieldtype: "Select",
			label: "Kind",
			options: [{ value: "Paid" }, "Draft"],
		},
	]
	assert.deepEqual(offered(await sheetHtml(config)), [
		{ label: "Paid", value: "Paid" },
		{ label: "Draft", value: "Draft" },
	])
})

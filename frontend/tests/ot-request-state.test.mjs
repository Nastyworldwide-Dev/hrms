import test from "node:test"
import assert from "node:assert/strict"
import vm from "node:vm"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"
import {
	computed,
	ref,
	reactive,
	shallowRef,
	watch,
	effectScope,
	nextTick,
} from "vue"
const require = createRequire(import.meta.url)
const { parse } = require("acorn")
const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8")
const script = (path) =>
	read(path).split("<script setup>")[1].split("</script>")[0]
const executable = (text) =>
	text
		.replace(/^import\s+[\s\S]*?from\s+["'][^"']+["']\s*\n/gm, "")
		.replace(/export default /g, "")
		.replace(/export /g, "")
function declaration(path, name) {
	const source = script(path)
	const node = parse(source, {
		ecmaVersion: "latest",
		sourceType: "module",
	}).body.find(
		(n) =>
			n.id?.name === name || n.declarations?.some((d) => d.id.name === name)
	)
	return node ? source.slice(node.start, node.end) : ""
}
const tick = async () => {
	await nextTick()
	await Promise.resolve()
	await Promise.resolve()
}
const ot = "../src/views/ot/OTRequestForm.vue",
	form = "../src/components/FormView.vue"
function fixture(id) {
	const calls = [],
		scope = effectScope(),
		employee = reactive({ data: { name: "EMP-A" } })
	const context = vm.createContext({
		computed,
		ref,
		reactive,
		shallowRef,
		watch,
		Event,
		settings: { data: {} },
		console: { info() {}, debug() {}, warn() {} },
		getConfig: () => undefined,
		saveLocal: (key) => assert.equal(key, null),
		request: (options) =>
			new Promise((resolve, reject) =>
				calls.push({ options, resolve, reject })
			),
		defineProps: () => reactive({ id }),
		inject: (key) =>
			key === "$employee"
				? employee
				: key === "$translate"
				? (s, args = []) => s.replace(/\{(\d+)\}/g, (_, i) => args[i])
				: () => ({ format: () => "date" }),
	})
	vm.runInContext(
		executable(read("../node_modules/frappe-ui/src/resources/resources.js")),
		context
	)
	const run = (code) => vm.runInContext(code, context)
	scope.run(() => run(executable(script(ot))))
	const fields = [
		{ fieldname: "ot_date", fieldtype: "Date", label: "Date", reqd: 1 },
		{
			fieldname: "claimed_hours",
			fieldtype: "Float",
			label: "Claimed Hours",
			reqd: 1,
		},
		{
			fieldname: "explanation",
			fieldtype: "Small Text",
			label: "Explanation",
			reqd: 1,
		},
	]
	calls
		.find((c) => c.options.url.endsWith(".get_doctype_fields"))
		.resolve(fields)
	const summaries = () =>
		calls.filter((c) => c.options.url.endsWith(".get_ot_claim_summary"))
	return {
		calls,
		context,
		employee,
		run,
		summaries,
		stop: () => scope.stop(),
		replace: (values) => {
			context.patch = values
			run("otRequest.value=patch")
		},
		set: (values) => {
			context.patch = values
			run("Object.assign(otRequest.value,patch)")
		},
	}
}
const resolve = (call, hours = 1.5) =>
	call.resolve({
		punch_ot_hours: hours,
		shift: "SHIFT",
		compensation: "Overtime Pay",
	})

test("all response orders apply only the selected day cap to summary and model", async () => {
	for (const order of [
		[0, 1, 2],
		[0, 2, 1],
		[1, 0, 2],
		[1, 2, 0],
		[2, 0, 1],
		[2, 1, 0],
	]) {
		const s = fixture()
		await tick()
		for (const date of ["2026-09-01", "2026-09-02", "2026-09-03"]) {
			s.set({ ot_date: date })
			await tick()
		}
		assert.equal(s.summaries().length, 3)
		for (const i of order) {
			resolve(s.summaries()[i], i === 2 ? 1.234567891 : 8 + i)
			await tick()
		}
		assert.equal(s.run("otRequest.value.claimed_hours"), 1.234567891)
		assert.equal(s.run("otRequest.value.punch_ot_hours"), 1.234567891)
		assert.equal(s.run("otSummary.value.data.punch_ot_hours"), 1.234567891)
		s.stop()
	}
})

test("date changes clear claim immediately, errors block saves, and retry keeps the selected identity", async () => {
	const s = fixture()
	await tick()
	s.set({ ot_date: "2026-09-03" })
	await tick()
	resolve(s.summaries()[0])
	await tick()
	s.set({ ot_date: "2026-09-04" })
	assert.equal(s.run("otRequest.value.claimed_hours"), null)
	assert.ok(s.run("saveError.value"))
	await tick()
	s.summaries()[1].reject(new Error("synthetic unavailable"))
	await tick()
	assert.ok(s.run("saveError.value"))
	assert.equal(s.run("otRequest.value.punch_ot_hours"), null)
	s.run("loadSummary()")
	resolve(s.summaries().at(-1), 2)
	await tick()
	assert.equal(s.run("saveError.value"), "")
	assert.equal(s.run("otRequest.value.claimed_hours"), 2)
	s.set({ ot_date: "" })
	assert.equal(s.run("otRequest.value.claimed_hours"), null)
	assert.ok(s.run("saveError.value"))
	s.stop()
})

test("employee changes invalidate pending day responses", async () => {
	const s = fixture()
	await tick()
	s.set({ ot_date: "2026-09-03" })
	await tick()
	s.employee.data.name = "EMP-B"
	await tick()
	assert.equal(s.summaries().at(-1).options.params.employee, "EMP-B")
	resolve(s.summaries().at(-1), 3)
	await tick()
	resolve(s.summaries()[0], 9)
	await tick()
	assert.equal(s.run("otRequest.value.claimed_hours"), 3)
	s.stop()
})

test("draft load and redundant fetch preserve a lower claim; a changed day gets its own cap", async () => {
	const s = fixture("OT-DRAFT")
	await tick()
	s.replace({
		name: "OT-DRAFT",
		employee: "EMP-A",
		ot_date: "2026-09-03",
		docstatus: 0,
		claimed_hours: 0.75,
		explanation: "Saved reason",
	})
	await tick()
	assert.equal(s.summaries().length, 1)
	resolve(s.summaries()[0], 1.5)
	await tick()
	assert.equal(s.run("otRequest.value.claimed_hours"), 0.75)
	s.set({ explanation: "Edited reason" })
	await tick()
	assert.equal(s.summaries().length, 1)
	s.run("loadSummary()")
	resolve(s.summaries().at(-1), 1.5)
	await tick()
	assert.equal(s.run("otRequest.value.claimed_hours"), 0.75)
	s.set({ ot_date: "2026-09-04" })
	await tick()
	resolve(s.summaries().at(-1), 2.5)
	await tick()
	assert.equal(s.run("otRequest.value.claimed_hours"), 2.5)
	s.stop()
})

test("actual FormView save refuses an unsettled OT summary and preserves mandatory explanation", async () => {
	for (const cap of [1.234567891, 0.016666667, 3.233333333]) {
		const s = fixture()
		await tick()
		s.set({ claimed_hours: 1.5, ot_date: "2026-09-03", explanation: "Reason" })
		await tick()
		const writes = [],
			props = {
				id: undefined,
				fields: s.run("formFields.data"),
				get saveError() {
					return s.run("saveError.value")
				},
			}
		const context = vm.createContext({
			props,
			formModel: s.run("otRequest"),
			formErrorMessage: ref(""),
			emit: () => s.run("validateForm()"),
			docList: { insert: { submit: (doc) => writes.push({ ...doc }) } },
			fileAttachments: ref([]),
		})
		vm.runInContext(
			["validateMandatoryFields", "handleDocInsert", "saveForm"]
				.map((n) => declaration(form, n))
				.join("\n"),
			context
		)
		vm.runInContext("saveForm()", context)
		assert.equal(writes.length, 0)
		resolve(s.summaries()[0], cap)
		await tick()
		s.set({ explanation: "" })
		vm.runInContext("saveForm()", context)
		assert.equal(writes.length, 0)
		s.set({ explanation: "Reason" })
		vm.runInContext("saveForm()", context)
		assert.equal(writes.length, 1)
		assert.equal(writes[0].claimed_hours, cap)
		s.stop()
	}
})

test("numeric zero remains visible and survives FormField default initialization", () => {
	const path = "../src/components/FormField.vue"
	for (const fieldtype of ["Float", "Int", "Currency"]) {
		const emitted = [],
			context = vm.createContext({
				computed,
				props: { fieldtype, readOnly: true, modelValue: 0, default: 7 },
				emit: (...args) => emitted.push(args),
			})
		vm.runInContext(
			["isLayoutField", "isNumberType", "showField", "setDefaultValue"]
				.map((n) => declaration(path, n))
				.join("\n"),
			context
		)
		assert.equal(vm.runInContext("showField.value", context), true)
		vm.runInContext("setDefaultValue()", context)
		assert.equal(emitted.length, 0)
	}
})

test("zero hours is a real zero, while malformed summaries remain retryable errors", async () => {
	for (const result of [
		{ punch_ot_hours: 0, compensation: "Overtime Pay" },
		{ punch_ot_hours: null, compensation: "Overtime Pay" },
		{ punch_ot_hours: 1, compensation: "Unknown" },
	]) {
		const s = fixture()
		await tick()
		s.set({ ot_date: "2026-09-03" })
		await tick()
		s.summaries()[0].resolve(result)
		await tick()
		assert.ok(s.run("saveError.value"))
		if (result.punch_ot_hours === 0) {
			assert.equal(s.run("otRequest.value.claimed_hours"), 0)
			assert.equal(s.run("otSummary.value.error"), null)
		} else {
			assert.equal(s.run("otRequest.value.claimed_hours"), null)
			assert.ok(s.run("otSummary.value.error"))
		}
		s.stop()
	}
})

test("late failure does not replace a current success; available-day lists also follow employee", async () => {
	const s = fixture()
	await tick()
	s.set({ ot_date: "2026-09-03" })
	await tick()
	s.employee.data.name = "EMP-B"
	await tick()
	resolve(s.summaries()[1], 2)
	await tick()
	s.summaries()[0].reject(new Error("obsolete failure"))
	await tick()
	assert.equal(s.run("saveError.value"), "")
	const days = s.calls.filter((c) =>
		c.options.url.endsWith(".get_claimable_ot_summary")
	)
	assert.equal(days.length, 2)
	days[1].resolve({
		compensation: "Replacement Leave",
		days: [{ date: "2026-09-04", hours: 8 }],
	})
	await tick()
	days[0].resolve({
		compensation: "Overtime Pay",
		days: [{ date: "2026-09-03", hours: 9 }],
	})
	await tick()
	assert.equal(
		s.run("claimableDays.value.data.compensation"),
		"Replacement Leave"
	)
	s.stop()
})

test("reloading a saved draft preserves its lower claim and refreshes the cap", async () => {
	const s = fixture("OT-DRAFT")
	await tick()
	s.replace({
		name: "OT-DRAFT",
		employee: "EMP-A",
		ot_date: "2026-09-03",
		docstatus: 0,
		claimed_hours: 0.75,
		modified: "first",
	})
	await tick()
	resolve(s.summaries().at(-1), 1.5)
	await tick()
	s.replace({
		name: "OT-DRAFT",
		employee: "EMP-A",
		ot_date: "2026-09-03",
		docstatus: 0,
		claimed_hours: 0.5,
		modified: "second",
	})
	await tick()
	resolve(s.summaries().at(-1), 1)
	await tick()
	assert.equal(s.run("otRequest.value.claimed_hours"), 0.5)
	assert.equal(s.run("otRequest.value.punch_ot_hours"), 1)
	s.employee.data.name = "EMP-B"
	s.set({ employee: "EMP-B" })
	await tick()
	assert.equal(s.summaries().at(-1).options.params.employee, "EMP-B")
	resolve(s.summaries().at(-1), 2)
	await tick()
	assert.equal(s.run("otRequest.value.claimed_hours"), 2)
	s.run("validateForm()")
	assert.equal(s.run("otRequest.value.employee"), "EMP-B")
	s.stop()
})

test("foreign and submitted drafts remain untouched so review is not dirtied by cap autofill", async () => {
	for (const record of [
		{ employee: "OTHER", docstatus: 0 },
		{ employee: "EMP-A", docstatus: 1 },
	]) {
		const s = fixture("OT-DRAFT")
		await tick()
		const doc = {
			name: "OT-DRAFT",
			ot_date: "2026-09-03",
			claimed_hours: 1.5,
			punch_ot_hours: 1.5,
			compensation: "Overtime Pay",
			modified: "first",
			...record,
		}
		s.replace(doc)
		await tick()
		const before = JSON.stringify(s.run("otRequest.value"))
		let edits = 0
		const stop = watch(s.run("otRequest"), () => edits++, { deep: true })
		s.run("loadSummary()")
		await tick()
		assert.equal(s.summaries().length, 0)
		assert.equal(JSON.stringify(s.run("otRequest.value")), before)
		assert.equal(edits, 0)
		if (record.docstatus === 0) {
			const review = vm.createContext({
				computed,
				props: { id: "OT-DRAFT", doctype: "OT Request" },
				isFormDirty: ref(edits > 0),
				workflow: ref(null),
				REQUEST_SUMMARY_FIELDS: { "OT Request": [] },
				decisionCapability: { actions: ref(["Approved", "Rejected"]) },
			})
			vm.runInContext(declaration(form, "canReview"), review)
			assert.equal(
				vm.runInContext("canReview.value", review),
				true,
				"an authorized reviewer can still enter the sheet"
			)
		}
		assert.equal(s.run("saveError.value"), "")
		stop()
		s.stop()
	}
})

test("storage-precision caps and intentionally lower claims survive editing and retries", async () => {
	for (const hours of [0.016666667, 3.233333333]) {
		const s = fixture()
		await tick()
		s.set({ ot_date: "2026-09-03" })
		await tick()
		resolve(s.summaries()[0], hours)
		await tick()
		assert.equal(s.run("otRequest.value.claimed_hours"), hours)
		s.set({ explanation: "Unrelated edit" })
		await tick()
		assert.equal(s.run("otRequest.value.claimed_hours"), hours)
		assert.equal(s.run("saveError.value"), "")
		s.set({ claimed_hours: 0.01 })
		s.run("loadSummary()")
		resolve(s.summaries().at(-1), hours)
		await tick()
		assert.equal(s.run("otRequest.value.claimed_hours"), 0.01)
		s.set({ claimed_hours: 3.24 })
		assert.match(s.run("saveError.value"), /Cannot claim more/)
		s.stop()
	}
})

test("the OT introduction is inside FormView's slot below its existing header", () => {
	const { parse: parseTemplate } = require("@vue/compiler-dom")
	const walk = (node, visit) => {
		visit(node)
		for (const child of node.children || []) walk(child, visit)
	}
	const formTree = parseTemplate(read(form).split("<script setup>")[0])
	let header, slot
	walk(formTree, (n) => {
		if (n.tag === "header" && !header) header = n
		if (
			n.tag === "slot" &&
			n.props?.some(
				(p) => p.name === "name" && p.value?.content === "beforeFields"
			)
		)
			slot = n
	})
	assert.ok(header && slot)
	assert.ok(header.loc.end.offset < slot.loc.start.offset)
	const otTree = parseTemplate(read(ot).split("<script setup>")[0])
	let introduction
	walk(otTree, (n) => {
		if (
			n.tag === "template" &&
			n.props?.some(
				(p) => p.name === "slot" && p.arg?.content === "beforeFields"
			)
		)
			introduction = n
	})
	assert.ok(introduction)
	assert.match(introduction.loc.source, /Days you can claim/)
	assert.doesNotMatch(
		script(ot),
		/This pays out as overtime|Your overtime pays out/
	)
})

test("own saved Open and Approved drafts stay pristine after an unchanged delayed cap", async () => {
	for (const status of ["Open", "Approved"]) {
		for (const editWhileLoading of [false, true]) {
			const s = fixture("OT-DRAFT")
			await tick()
			const context = vm.createContext({
				watch,
				computed,
				props: { id: "OT-DRAFT", doctype: "OT Request" },
				formModel: s.run("otRequest"),
				isFormReady: ref(true),
				isFormUpdated: ref(false),
				isFormDirty: ref(false),
				workflow: ref(null),
				REQUEST_SUMMARY_FIELDS: { "OT Request": [] },
				decisionCapability: {
					actions: ref(
						status === "Approved" ? ["Submit"] : ["Approved", "Rejected"]
					),
				},
			})
			const source = script(form),
				start = source.indexOf("watch(\n\t() => formModel.value,"),
				end = source.indexOf("\n\nwatch(", start)
			vm.runInContext(
				source.slice(start, end) + "\n" + declaration(form, "canReview"),
				context
			)
			s.replace({
				name: "OT-DRAFT",
				employee: "EMP-A",
				ot_date: "2026-09-03",
				docstatus: 0,
				status,
				claimed_hours: 1.5,
				punch_ot_hours: 1.5,
				shift: "SHIFT",
				compensation: "Overtime Pay",
				modified: "first",
				explanation: "Saved",
			})
			await tick()
			context.isFormDirty.value = false
			assert.ok(
				s.run("saveError.value"),
				"unchanged visible values still cannot save while capacity loads"
			)
			if (editWhileLoading) {
				s.set({ explanation: "Real unsaved edit" })
				await tick()
			}
			resolve(s.summaries().at(-1), 1.5)
			await tick()
			assert.equal(
				context.isFormDirty.value,
				editWhileLoading,
				"capacity refresh must not invent or erase dirty state"
			)
			assert.equal(
				vm.runInContext("canReview.value", context),
				!editWhileLoading
			)
			assert.equal(
				s.run("otRequest.value.explanation"),
				editWhileLoading ? "Real unsaved edit" : "Saved"
			)
			assert.equal(s.run("saveError.value"), "")
			s.stop()
		}
	}
})

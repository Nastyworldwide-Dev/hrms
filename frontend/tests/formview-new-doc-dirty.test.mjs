// A NEW request form never armed the "unsaved changes" confirm: the dirty
// watcher returned at once when there was no props.id, so an employee who
// filled in expense items or an OT date and tapped Back lost it all silently.
// A new form has no server copy to diff against, so dirty means: it differs
// from what it held when the employee FIRST touched it. FormField's mount
// defaults and the seeds a parent applies after mount (approver, currency, an
// empty items table) are not the employee's work and must not prompt.
// Run: cd frontend && node --test tests/formview-new-doc-dirty.test.mjs
import test from "node:test"
import assert from "node:assert/strict"
import vm from "node:vm"
import { readFileSync } from "node:fs"
import { createRequire } from "node:module"
import { computed, nextTick, reactive, ref, watch } from "vue"

const require = createRequire(import.meta.url)
const { parse } = require("acorn")
const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8")
const form = "../src/components/FormView.vue"
const script = read(form).split("<script setup>")[1].split("</script>")[0]
function declaration(name) {
	const node = parse(script, {
		ecmaVersion: "latest",
		sourceType: "module",
	}).body.find(
		(n) =>
			n.id?.name === name || n.declarations?.some((d) => d.id.name === name)
	)
	assert.ok(node, `FormView declares ${name}`)
	return script.slice(node.start, node.end)
}
const watcherStart = script.indexOf("watch(\n\t() => formModel.value,")
const watcher = script.slice(
	watcherStart,
	script.indexOf("\n\nwatch(", watcherStart)
)
const tick = async () => {
	await nextTick()
	await Promise.resolve()
}

test("the dirty watcher no longer ignores a form without an id", () => {
	assert.doesNotMatch(watcher, /if \(!props\.id\) return/)
	assert.match(watcher, /newDocBaseline/)
})

test("a new form is dirty once the employee touches it and it differs from its defaults", async () => {
	const model = ref({})
	const context = vm.createContext({
		watch,
		computed,
		ref,
		props: reactive({
			id: undefined,
			fields: [
				{ fieldname: "ot_date", fieldtype: "Date" },
				{ fieldname: "explanation", fieldtype: "Small Text" },
				{ fieldname: "expenses", fieldtype: "Table" },
				{ fieldname: "expense_approver", fieldtype: "Link" },
				{ fieldname: "employee", fieldtype: "Link", hidden: 1 },
			],
		}),
		formModel: model,
		isFormReady: ref(true),
		isFormUpdated: ref(false),
		isFormDirty: ref(false),
	})
	vm.runInContext(
		[
			"newDocBaseline",
			"formTouched",
			"touchForm",
			"isEmptyValue",
			"editableSnapshot",
		]
			.map(declaration)
			.join("\n") +
			"\n" +
			watcher,
		context
	)

	// FormField seeds "" on mount; the parent seeds an approver and an empty
	// items table whenever its resources land
	model.value.ot_date = ""
	model.value.explanation = ""
	await tick()
	model.value.expense_approver = "boss@example.com"
	model.value.expenses = []
	model.value.employee = "EMP-A"
	await tick()
	assert.equal(
		context.isFormDirty.value,
		false,
		"seeds are not the employee's work"
	)

	// the employee touches the form (capture phase, before any edit), then types
	vm.runInContext("touchForm()", context)
	assert.equal(
		context.isFormDirty.value,
		false,
		"a touch alone changes nothing"
	)
	model.value.explanation = "Worked the late shift"
	await tick()
	assert.equal(context.isFormDirty.value, true, "typed work arms the confirm")

	// ...and adds an item
	model.value.explanation = ""
	model.value.expenses.push({ amount: 10 })
	await tick()
	assert.equal(context.isFormDirty.value, true, "an added item is work to lose")

	// ...then removes everything again: nothing left to lose
	model.value.expenses.pop()
	await tick()
	assert.equal(
		context.isFormDirty.value,
		false,
		"back to the defaults is clean"
	)
})

test("a loaded document keeps the existing dirty rule", () => {
	assert.match(watcher, /isFormReady\.value && !isFormUpdated\.value/)
})

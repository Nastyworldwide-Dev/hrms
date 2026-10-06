// alpha.38 S1: HR writes an SOP the way staff read it.
//
// Before: the Content field was a GTextarea fed `doc.content`, which is HTML, so
// HR saw "<p>…</p><img src=…>" and could not add a heading, list, bold, link or
// picture from Nadi. Now the sheet carries the same rich editor the form screens
// use (frappe-ui TextEditor), says in one line who will see the SOP, and can show
// the body "as staff see it" through the SAME safeHtml() + .sop-prose that
// SopDetail reads with.
//
// The sheet's real <script setup> is compiled and run (HelpdeskHub.test.js
// recipe); the server, the toast and the kit are the boundaries.
import assert from "node:assert/strict"
import { test } from "node:test"
import { readFileSync } from "node:fs"
import { compileScript, parse } from "@vue/compiler-sfc"
import { computed, nextTick, reactive, ref, watch } from "vue"

import { departmentLabel } from "../../utils/departmentLabel.js"
import { safeHtml } from "../../utils/safeHtml.js"

const read = (name) => readFileSync(new URL(`../sop/${name}`, import.meta.url), "utf8")
const source = read("SopFormSheet.vue")
const descriptor = parse(source).descriptor
const template = descriptor.template.content
const script = compileScript(descriptor, { id: "sop-form-sheet" })
// static imports only (they start a line); the editor's dynamic import() stays
// in the code and is never called, because nothing renders here
const code = script.content
	.replace(/^import[\s\S]*?from ["'][^"']+["'];?$/gm, "")
	.replace("export default", "return")

const trimmed = (text) =>
	text
		.replace(/<!--[\s\S]*?-->/g, "")
		.replace(/\/\*[\s\S]*?\*\//g, "")
		.replace(/(^|[^:])\/\/[^\n]*/g, "$1")

/** The sheet, with the server standing behind createResource / createListResource. */
function sheet({ sopName = null, doc = null, company = "" } = {}) {
	const calls = []
	const inserts = []
	const responses = {
		"hrms.api.sop.get_sop": doc,
		"frappe.client.get_value": { company },
		"frappe.client.set_value": {},
		"hrms.api.sop.remove_attachment": {},
	}
	const bindings = {
		computed,
		reactive,
		ref,
		watch,
		useId: () => "sop-id",
		defineAsyncComponent: (loader) => loader,
		inject: () => (text, args = []) => text.replace(/\{(\d+)\}/g, (_, i) => args[i]),
		departmentLabel,
		safeHtml,
		personalCacheKey: (key) => key,
		firstMessage: (error, fallback) => fallback || String(error),
		gToast: () => {},
		createResource(options) {
			return {
				fetch(params) {
					calls.push({ url: options.url, params })
					const answer = responses[options.url]
					if (options.onSuccess && answer !== undefined && answer !== null) options.onSuccess(answer)
					return Promise.resolve(answer)
				},
			}
		},
		createListResource(options) {
			if (options.doctype === "Department") return { data: [{ name: "Production - NW0A" }] }
			return {
				insert: {
					data: null,
					submit: (values) => {
						inserts.push(values)
						return Promise.resolve({ name: "HR-SOP-00009" })
					},
				},
			}
		},
		console: { info() {}, warn() {}, error() {} },
		window: { location: { hostname: "fresh.local" } },
	}
	for (const name of Object.keys(script.imports)) if (!(name in bindings)) bindings[name] = {}
	const component = new Function(...Object.keys(bindings), code)(...Object.values(bindings))
	const props = reactive({ open: false, sopName })
	const emitted = []
	const vm = component.setup(props, {
		expose() {},
		emit: (...args) => emitted.push(args),
	})
	return {
		vm,
		props,
		calls,
		inserts,
		emitted,
		/** what the sheet asked set_value to write */
		written: () => calls.filter((c) => c.url === "frappe.client.set_value").map((c) => c.params.fieldname),
		open: async () => {
			props.open = true
			await nextTick()
		},
	}
}

const EDITOR_HTML =
	"<h2>Cash handling</h2><ol><li>Count the float</li><li>Sign the sheet</li></ol><p>Never <strong>skip</strong> step 2.</p>"

// ---- 1. the sheet renders the rich editor, not a textarea ------------------

test("Content is the rich TextEditor, not a textarea", () => {
	assert.match(template, /<TextEditor[\s>]/, "the sheet renders TextEditor")
	assert.doesNotMatch(template, /<GTextarea[\s>]/, "no plain text area for the body")
	assert.doesNotMatch(trimmed(source), /GTextarea/, "and no leftover import of it")
})

test("the editor is wired as FormField wires it: async import, change, fixed menu, Glass wrapper", () => {
	assert.match(
		trimmed(source),
		/defineAsyncComponent\(\(\) => import\("frappe-ui\/src\/components\/TextEditor\/TextEditor\.vue"\)\)/,
		"loaded on demand, so the editor stays out of every page's first download"
	)
	const editor = template.match(/<TextEditor[\s\S]*?\/>/)?.[0] || ""
	assert.match(editor, /:content="form\.content"/)
	assert.match(editor, /@change="[^"]*form\.content = /, "an edit writes the HTML back into the form")
	assert.match(editor, /:fixedMenu="true"/)
	assert.match(template, /<div[^>]*class="g-texteditor"[^>]*>\s*<TextEditor/, "inside the Glass wrapper")
})

test("the editor has an accessible name tied to the visible Content label", () => {
	const wrapper = template.match(/<div[^>]*class="g-texteditor"[^>]*>/)?.[0] || ""
	const named = /aria-label=/.test(wrapper) || /aria-labelledby=/.test(wrapper)
	assert.ok(named, "the editor group is named")
	assert.match(wrapper, /role="group"/)
	if (/aria-labelledby=/.test(wrapper)) {
		assert.match(template, /<span[^>]*:id="[^"]+"[^>]*>\s*\{\{ __\("Content"\) \}\}/, "pointing at the visible label")
	}
})

// ---- 2. save sends the editor's HTML as it is -----------------------------

test("saving a new SOP posts the editor HTML unchanged", async () => {
	const { vm, inserts } = sheet()
	vm.form.title = "Cash Handling"
	vm.form.content = EDITOR_HTML
	await vm.save()
	assert.equal(inserts.length, 1)
	assert.equal(inserts[0].content, EDITOR_HTML)
})

test("saving an edit posts the editor HTML unchanged", async () => {
	const doc = { title: "Cash", scope: "General", department: "", pinned: 0, published: 1, content: "<p>old</p>" }
	const { vm, props, written, open } = sheet({ sopName: "HR-SOP-00001", doc })
	await open()
	assert.equal(props.sopName, "HR-SOP-00001")
	vm.form.content = EDITOR_HTML
	await vm.save()
	assert.equal(written().length, 1)
	assert.equal(written()[0].content, EDITOR_HTML)
})

test("an SOP that already holds HTML opens as that HTML and saves back byte for byte", async () => {
	const stored = '<p>Private picture:</p><img src="/private/files/till.png">'
	const doc = { title: "Till", scope: "General", department: "", pinned: 0, published: 1, content: stored }
	const { vm, written, open } = sheet({ sopName: "HR-SOP-00002", doc })
	await open()
	assert.equal(vm.form.content, stored, "the editor is fed the HTML, not wrapped or escaped")
	await vm.save()
	assert.equal(written()[0].content, stored)
})

// ---- 3. legacy plain text is wrapped once ---------------------------------

test("an old plain-text SOP opens as paragraphs, wrapped once", async () => {
	const doc = {
		title: "Old",
		scope: "General",
		department: "",
		pinned: 0,
		published: 1,
		content: "Lock up.\nSwitch off the lights.\n\nSet the alarm & leave.",
	}
	const { vm, written, open } = sheet({ sopName: "HR-SOP-00003", doc })
	await open()
	const wrapped = "<p>Lock up.<br>Switch off the lights.</p><p>Set the alarm &amp; leave.</p>"
	assert.equal(vm.form.content, wrapped, "the editor gets paragraphs it can show")
	await vm.save()
	assert.equal(written()[0].content, wrapped, "saved as it was shown, not wrapped a second time")
})

// ---- 4. who will see it ----------------------------------------------------

test("General says Everyone", () => {
	const { vm } = sheet()
	vm.form.scope = "General"
	assert.equal(vm.whoSees.value, "Everyone")
})

test("General with a company says Everyone in that company", async () => {
	const doc = { title: "Co", scope: "General", department: "", pinned: 0, published: 1, content: "" }
	const { vm, calls, open } = sheet({ sopName: "HR-SOP-00004", doc, company: "Nasty Worldwide Sdn Bhd" })
	await open()
	const lookup = calls.find((c) => c.url === "frappe.client.get_value")
	assert.deepEqual(
		lookup?.params,
		{ doctype: "SOP Document", fieldname: "company", filters: { name: "HR-SOP-00004" } },
		"the company is read from the SOP itself (get_sop does not carry it)"
	)
	assert.equal(vm.whoSees.value, "Everyone in Nasty Worldwide Sdn Bhd")
})

test("a blank company is not mentioned", async () => {
	const doc = { title: "Blank", scope: "General", department: "", pinned: 0, published: 1, content: "" }
	const { vm, open } = sheet({ sopName: "HR-SOP-00005", doc, company: "" })
	await open()
	assert.equal(vm.whoSees.value, "Everyone")
})

test("Department says Only that department, without the company suffix", () => {
	const { vm } = sheet()
	vm.form.scope = "Department"
	vm.form.department = "Production - NW0A"
	assert.equal(vm.whoSees.value, "Only Production")
})

test("the who-sees line sits under Scope and reads aloud as a status", () => {
	const tpl = template
	const scopeAt = tpl.indexOf("<GSegmented")
	const lineAt = tpl.indexOf("whoSees")
	assert.ok(scopeAt >= 0 && lineAt > scopeAt, "after the Scope control")
	assert.match(tpl, /<p[^>]*class="g-form-footer"[^>]*>\s*\{\{ whoSees \}\}/)
})

// ---- 5. "As staff see it" --------------------------------------------------

test("the preview renders through safeHtml and the sop-prose class SopDetail reads with", () => {
	assert.match(template, /<div[^>]*class="sop-prose"[^>]*v-html="safeHtml\(/)
	assert.match(trimmed(source), /import \{ safeHtml \} from "@\/utils\/safeHtml"/)
	assert.doesNotMatch(trimmed(source), /ALLOWED_TAGS|ALLOWED_ATTRS/, "the allow-list is not copied")
	assert.match(read("SopDetail.vue"), /class="sop-prose" v-html="safeHtml\(sop\.data\.content\)"/, "the reader is unchanged")
})

test("the preview is a switch beside the editor, off until HR asks", () => {
	const { vm } = sheet()
	assert.equal(vm.mode.value, "write", "opens on the editor")
	assert.match(trimmed(source), /label: "As staff see it"/, "the second segment is the preview")
	assert.match(template, /<GSegmented[^>]*v-model="mode"/)
	// the editor stays mounted while previewing, so nothing HR typed is lost
	assert.match(template, /v-show="mode === 'write'"[^>]*class="g-texteditor"|class="g-texteditor"[^>]*v-show="mode === 'write'"/)
})

test("a new sheet always opens on the editor, even after a preview", async () => {
	const { vm, open, props } = sheet()
	vm.mode.value = "preview"
	await open()
	assert.equal(vm.mode.value, "write")
	assert.equal(props.open, true)
})

test("the reading styles have one owner: the theme, loaded on every screen", () => {
	// The reader (SopDetail) and HR's preview (the sheet) both draw .sop-prose; one
	// global rule set in the theme, so staff and HR always see the same thing.
	const theme = readFileSync(new URL("../../theme/glass-components.css", import.meta.url), "utf8")
	assert.match(theme, /\.sop-prose h2/, "the theme carries the reading styles")
	assert.doesNotMatch(read("SopDetail.vue"), /\.sop-prose\s*[{,]/, "SopDetail keeps only the class")
	assert.doesNotMatch(read("SopFormSheet.vue"), /\.sop-prose\s*[{,]/, "the sheet keeps only the class")
})

test("a department SOP with no department picked yet does not say 'Only '", () => {
	const { vm } = sheet()
	vm.form.scope = "Department"
	assert.equal(vm.whoSees.value, "Only the department you pick")
})

test("an empty editor (<p></p>) is saved as empty, so the reader shows its empty state", async () => {
	const { vm, inserts } = sheet()
	vm.form.title = "Blank"
	vm.form.content = "<p></p>"
	await vm.save()
	assert.equal(inserts[0].content, "")
})

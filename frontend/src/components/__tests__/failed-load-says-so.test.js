// L1b (alpha.38): four parts drew NOTHING when their own read failed -- the same
// blank that hid four faults for a week (utils/loudRequest.js). Each now draws
// the app's one failure line, ResourceError, with Try again, in place.
//
// RequestTimeline is rendered for real (compileScript + SSR, the
// resource-error-no-access.test.js recipe) with the failing resource as the
// boundary; the other three are source-asserted because their templates sit
// behind Ionic / the modal kit, which the node runner does not compile.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { compileScript, parse } from "@vue/compiler-sfc"
import { createSSRApp, h, inject, mergeProps, unref, computed } from "vue"
import {
	renderToString,
	ssrRenderAttrs,
	ssrRenderComponent,
	ssrRenderList,
	ssrInterpolate,
	ssrRenderVNode,
} from "vue/server-renderer"

const read = (p) => readFileSync(new URL(p, import.meta.url), "utf8")
// comments stripped, so a note ABOUT the old blank cannot satisfy a test
const code = (text) =>
	text
		.replace(/<!--[\s\S]*?-->/g, "")
		.replace(/\/\*[\s\S]*?\*\//g, "")
		.replace(/(^|[^:])\/\/[^\n]*/g, "$1")
const template = (src) => src.slice(src.indexOf("<template>"), src.lastIndexOf("</template>"))

// ---- RequestTimeline, executed ----------------------------------------------------------------

async function renderTimeline({ error = null, data = null }) {
	const source = read("../RequestTimeline.vue")
	const { descriptor } = parse(source)
	const script = compileScript(descriptor, {
		id: "request-timeline",
		inlineTemplate: true,
		templateOptions: { ssr: true, ssrCssVars: [] },
	})
	const body = script.content
		.replace(/^import[\s\S]*?from ["'][^"']+["'];?$/gm, "")
		.replace("export default", "return")
	const ResourceErrorStub = {
		props: ["resource", "what"],
		render() {
			return h("div", { role: "alert", class: "stub-error" }, `Could not load ${this.what}.`)
		},
	}
	const Passthrough = { render() { return h("div", this.$slots.default?.()) } }
	const bindings = {
		computed,
		inject,
		unref,
		_unref: unref,
		_mergeProps: mergeProps,
		_ssrRenderAttrs: ssrRenderAttrs,
		_ssrRenderComponent: ssrRenderComponent,
		_ssrRenderList: ssrRenderList,
		_ssrInterpolate: ssrInterpolate,
		_ssrRenderVNode: ssrRenderVNode,
		_createVNode: h,
		createResource: () => ({ error, data }),
		ResourceError: ResourceErrorStub,
		GListPanel: Passthrough,
		GListRow: Passthrough,
		TILE: { neutral: "n" },
		siteTime: () => ({ isValid: () => false }),
		timelineLine: () => "line",
		Check: {}, Clock: {}, Send: {}, X: {}, Ban: {},
		console: { warn() {}, info() {} },
	}
	const component = new Function(...Object.keys(bindings), body)(...Object.values(bindings))
	const app = createSSRApp({
		render: () => h(component, { doctype: "Leave Application", name: "HR-LAP-1" }),
	})
	app.provide("$translate", (t) => t)
	return renderToString(app)
}

test("RequestTimeline: a history that failed to load says so, with ResourceError", async () => {
	const html = await renderTimeline({ error: new Error("boom") })
	assert.match(html, /Could not load this request&#39;s history\./)
	assert.match(html, /role="alert"/)
})

test("RequestTimeline: a history that loaded with only 'Sent' still draws nothing", async () => {
	const html = await renderTimeline({ data: [{ what: "sent", who: "A", when: "2026-10-06" }] })
	assert.doesNotMatch(html, /alert|History/)
})

// ---- the three others, by their source -------------------------------------------------------

test("ExpensesTable: the sheet says so when its field list or the claim types failed", () => {
	const src = code(read("../ExpensesTable.vue"))
	const tpl = template(src)
	assert.match(src, /import ResourceError from "@\/components\/ResourceError\.vue"/)
	assert.match(tpl, /<ResourceError\s+v-if="expensesTableFields\.error"\s+:resource="expensesTableFields"/)
	assert.match(tpl, /v-else-if="claimTypesResource\.error"\s+:resource="claimTypesResource"/)
	assert.match(src, /if \(expensesTableFields\.error\) return true/, "no Add on a form with no fields")
})

test("ExpenseTaxesTable: the sheet says so when its field list failed", () => {
	const src = code(read("../ExpenseTaxesTable.vue"))
	assert.match(src, /import ResourceError from "@\/components\/ResourceError\.vue"/)
	assert.match(template(src), /<ResourceError\s+v-if="taxesTableFields\.error"\s+:resource="taxesTableFields"/)
	assert.match(src, /if \(taxesTableFields\.error\) return true/, "no Add on a form with no fields")
})

test("MustReadNotice: a notice body that failed says so, and never blocks the page", () => {
	const src = code(read("../MustReadNotice.vue"))
	const tpl = template(src)
	assert.match(tpl, /<ResourceError\s+v-else-if="detail\.error"\s+:resource="bodyResource"/)
	// Try again re-opens the body (so 'read to the end' is measured on what arrives), not a bare reload
	assert.match(src, /reload: \(\) => \(current\.value \? openBody\(current\.value\.name\) : undefined\)/)
	// the full-screen page keeps its way out: the confirm button and 'Remind me later' are not behind the error
	const foot = tpl.indexOf('<footer class="g-mustread__foot">')
	assert.ok(foot > tpl.indexOf("<ResourceError"), "the footer comes after, outside the error branch")
})

test("MustReadNotice: a failed notice LIST shows nothing, on purpose (logged, never blocks the app)", () => {
	const src = read("../MustReadNotice.vue")
	assert.match(src, /queue\.fetch\(\)\?\.catch\?\.\(\(\) => console\.warn\("\[MustRead\] queue unavailable"\)\)/)
	assert.doesNotMatch(template(code(src)), /queue\.error/, "no error state for the list: it is a full-screen modal")
})

// ---- L1a follow-through: the one write whose only voice was the seam's toast -----------------

test("TicketDetail: a refused reply says why itself, since the seam stays quiet for it", () => {
	const src = code(read("../../views/helpdesk/TicketDetail.vue"))
	const send = src.slice(src.indexOf("async function send()"))
	assert.match(send, /gToast\(\{ title: __\("Reply not sent"\), text: firstMessage\(error\), variant: "error" \}\)/)
	assert.match(read("../../utils/requestFailure.js"), /"hrms\.api\.helpdesk\.reply"/)
})

test("MustReadNotice never records a notice whose text did not load", () => {
	const src = readFileSync(new URL("../MustReadNotice.vue", import.meta.url), "utf8")
	const confirm = src.match(/async function onConfirm\(\) \{[\s\S]*?\n\}/)?.[0] ?? ""
	const guard = confirm.indexOf("detail.error")
	assert.ok(guard > 0, "onConfirm checks for a failed load")
	assert.ok(guard < confirm.indexOf("reachedEnd"), "before anything else can run")
	assert.match(src, /failed: Boolean\(detail\.error\)/, "the button says it cannot confirm yet")
})

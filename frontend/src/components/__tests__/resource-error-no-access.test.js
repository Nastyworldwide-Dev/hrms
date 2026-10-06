// B2 (alpha.37): a page the person may not open said "Could not load this ...
// Try again" -- as if retrying could help -- or, in views that gate on
// `resource.data`, nothing at all. A server refusal (403 / PermissionError)
// from a signed-in person is a plain "You can't open this.", with the Back
// button where the screen asks for one. A 403 from a session that has ended
// stays what it was: sessionLost.js owns that, and the page reloads onto Login.
//
// Renders the REAL ResourceError.vue (compileScript + SSR template, the
// GTag.test.js recipe); the router, the user cookie and the button are the
// boundaries.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { compileScript, parse } from "@vue/compiler-sfc"
import { computed, createSSRApp, h, inject, mergeProps, unref } from "vue"
import {
	renderToString,
	ssrInterpolate,
	ssrRenderAttrs,
	ssrRenderComponent,
} from "vue/server-renderer"

import { isNoAccess } from "../../utils/sessionLost.js"

const source = readFileSync(new URL("../ResourceError.vue", import.meta.url), "utf8")
const { descriptor } = parse(source)
const script = compileScript(descriptor, {
	id: "resource-error",
	inlineTemplate: true,
	templateOptions: { ssr: true, ssrCssVars: [] },
})
const code = script.content
	.replace(/^import[\s\S]*?from ["'][^"']+["'];?$/gm, "")
	.replace("export default", "return")

const GButtonStub = {
	props: ["label"],
	render() {
		return h("button", { class: "stub-retry" }, this.label)
	},
}

async function render({ error, back = false, signedIn = true, what = "" }) {
	const bindings = {
		computed,
		inject,
		// the compiled template's own aliases (`import { unref as _unref }`)
		_unref: unref,
		_mergeProps: mergeProps,
		_ssrRenderAttrs: ssrRenderAttrs,
		_ssrRenderComponent: ssrRenderComponent,
		_ssrInterpolate: ssrInterpolate,
		GButton: GButtonStub,
		useRouter: () => ({}),
		goBackOrHome: () => {},
		isNoAccess,
		sessionUser: () => (signedIn ? "a@x" : null),
		console: { info() {}, warn() {}, error() {} },
	}
	const component = new Function(...Object.keys(bindings), code)(...Object.values(bindings))
	const app = createSSRApp({
		render: () => h(component, { resource: { error, reload() {} }, back, what }),
	})
	return renderToString(app)
}

const forbidden = (extra = {}) =>
	Object.assign(new Error("x"), {
		response: { status: 403 },
		exc_type: "PermissionError",
		...extra,
	})

test("a refusal from a signed-in person says 'You can't open this.' with Back", async () => {
	const html = await render({ error: forbidden(), back: true, what: "this employee's KPI" })
	assert.match(html, /You can&#39;t open this\./)
	assert.doesNotMatch(html, /Could not load/)
	assert.match(html, /Back/)
	assert.doesNotMatch(html, /Try again/, "retrying a refusal cannot help")
})

test("a refusal still honours the opt-in Back: no Back on an inline error", async () => {
	const html = await render({ error: forbidden(), back: false })
	assert.match(html, /You can&#39;t open this\./)
	assert.doesNotMatch(html, />Back</)
})

test("a PermissionError with no status is a refusal too", async () => {
	const html = await render({
		error: Object.assign(new Error("x"), { exc_type: "PermissionError" }),
	})
	assert.match(html, /You can&#39;t open this\./)
})

test("a 500 keeps today's message and Try again", async () => {
	const error = Object.assign(new Error("x"), { response: { status: 500 } })
	const html = await render({ error, what: "your leave balance" })
	assert.match(html, /Could not load your leave balance\./)
	assert.match(html, /Try again/)
	assert.doesNotMatch(html, /open this/)
})

test("a network failure keeps today's message", async () => {
	const html = await render({ error: new TypeError("Failed to fetch") })
	assert.match(html, /Could not load this\./)
})

test("a 403 from a session that has ended is NOT 'no access': today's message stays", async () => {
	// cookie says Guest: the session is gone and the page is on its way to Login
	const html = await render({ error: forbidden(), signedIn: false })
	assert.match(html, /Could not load this\./)
	assert.doesNotMatch(html, /open this/)
})

test("an AuthenticationError or SessionExpired is never 'no access', even carrying a 403", () => {
	assert.equal(
		isNoAccess(forbidden({ exc_type: "AuthenticationError" }), { signedIn: true }),
		false
	)
	assert.equal(isNoAccess(forbidden({ exc_type: "SessionExpired" }), { signedIn: true }), false)
	assert.equal(
		isNoAccess(Object.assign(new Error("x"), { response: { status: 401 } }), { signedIn: true }),
		false
	)
})

test("a list resource's error is read from the request that ran", async () => {
	const bindings = readFileSync(new URL("../ResourceError.vue", import.meta.url), "utf8")
	assert.match(bindings, /props\.resource\?\.list \?\? props\.resource/)
})

test("nothing at all renders when nothing failed", async () => {
	const html = await render({ error: null })
	assert.doesNotMatch(html, /role="alert"/)
})

// KpiDetail takes a `data` prop and owns no resource; the person-detail request
// (employeeKpi) lives in kpi/Dashboard.vue, which draws ResourceError for it
// directly under its own "Back to ..." link (a second Back from ResourceError
// there would be two Back buttons). So the 403 sentence reaches the KPI detail
// through THIS line: if it is removed, a refused KPI detail is blank again.
test("the KPI drill-down draws ResourceError for the person-detail request, beside one Back", () => {
	const dash = readFileSync(new URL("../../views/kpi/Dashboard.vue", import.meta.url), "utf8")
	const detail = dash.slice(dash.indexOf('v-else-if="openedName"'))
	assert.match(detail.slice(0, 2500), /<ResourceError :resource="employeeKpi"/)
	assert.doesNotMatch(
		detail.slice(0, 2500).match(/<ResourceError[^>]*>/)[0],
		/\bback\b/,
		"the drill-down already has its own Back link"
	)
})

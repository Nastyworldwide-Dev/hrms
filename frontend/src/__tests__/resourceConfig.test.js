// A failed auto-load must draw the page's error state, never an unhandled
// promise rejection (runtime crawl, 15 Sep 2026).
//
// frappe-ui's createResource fires `auto: true` with a bare `out.fetch()` —
// nobody awaits it — and its handleError always rethrows. So every missing
// document (/sop/<missing>, /leave-applications/<missing>, /helpdesk/<id>)
// reached the browser as `pageerror: …DoesNotExistError` for every persona, on
// top of the ResourceError the page already drew and the toast loudRequest
// already raised. The report was made; the rejection was just noise nobody
// could catch.
//
// Explicit actions still reject: a caller awaiting `.submit()` must see the
// failure to react to it.
//
// Runs frappe-ui's REAL resources.js. Its package imports are extensionless
// and one is TypeScript, so a resolve hook maps them for plain Node.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import * as nodeModule from "node:module"

// Bun (the commit gate's runner) resolves these natively and has no hook API.
nodeModule.registerHooks?.({
	resolve(specifier, context, next) {
		if (context.parentURL?.includes("/frappe-ui/src/") && specifier.startsWith(".")) {
			if (specifier.endsWith("/debounce"))
				return { url: "data:text/javascript,export default (fn) => fn", shortCircuit: true }
			if (!/\.[cm]?js$/.test(specifier)) return next(`${specifier}.js`, context)
		}
		return next(specifier, context)
	},
})

const { createResource } = await import("frappe-ui/src/resources/resources.js")

const source = readFileSync(new URL("../utils/loudRequest.js", import.meta.url), "utf8").replace(
	'import { toast } from "frappe-ui"',
	"const toast = () => {}"
)
const loudModule = new Function(
	`${source.replace(/export function/g, "function")}
	return {
		makeLoudRequest,
		swallowReportedRejection: typeof swallowReportedRejection === "function" ? swallowReportedRejection : null,
	}`
)()

const NOT_FOUND = { exc_type: "DoesNotExistError", messages: ["SOP Document SOP-X not found"] }
const quiet = { error() {} }

function loudFailing(error = NOT_FOUND) {
	return loudModule.makeLoudRequest(() => Promise.reject(error), { notify: () => {} })
}

// What the browser does with an unhandled rejection: dispatch a cancelable
// `unhandledrejection` event; only an uncancelled one becomes a pageerror.
function surfacesAsPageError(reason) {
	let prevented = false
	loudModule.swallowReportedRejection?.({ reason, preventDefault: () => (prevented = true) })
	return !prevented
}

test("an auto resource that fails shows its error state and raises no page error", async () => {
	// frappe-ui's auto path is `if (options.auto) out.fetch()` — the promise is
	// dropped. Both test runners fail a test on a truly unhandled rejection, so
	// this makes the same unawaited call and holds the promise itself: its
	// rejection reason is exactly what the browser's unhandledrejection sees.
	const resource = createResource({
		url: "/api/method/hrms.api.sop.get_sop",
		resourceFetcher: loudFailing(),
	})
	const reasons = []
	const originalConsole = console.error
	console.error = quiet.error
	try {
		await resource.fetch().catch((reason) => reasons.push(reason))
	} finally {
		console.error = originalConsole
	}
	assert.equal(resource.error?.exc_type, "DoesNotExistError", "ResourceError reads resource.error")
	assert.equal(resource.loading, false)
	assert.equal(reasons.length, 1, "the dropped auto-fetch promise rejects — the case under test")
	assert.deepEqual(
		reasons.filter(surfacesAsPageError).map((r) => r?.exc_type || String(r)),
		[],
		"a reported request failure must not surface as an unhandled rejection"
	)
})

test("an explicit submit still rejects so its caller can react", async () => {
	const resource = createResource({
		url: "/api/method/hrms.api.helpdesk.new_ticket",
		resourceFetcher: loudFailing({
			exc_type: "ValidationError",
			messages: ["Subject is required"],
		}),
	})
	const originalConsole = console.error
	console.error = quiet.error
	try {
		await assert.rejects(() => resource.submit({ subject: "" }), { exc_type: "ValidationError" })
	} finally {
		console.error = originalConsole
	}
})

test("a rejection that never passed through the request seam still surfaces", () => {
	assert.ok(
		loudModule.swallowReportedRejection,
		"loudRequest must export swallowReportedRejection"
	)
	assert.equal(surfacesAsPageError(new TypeError("x is undefined")), true)
	assert.equal(surfacesAsPageError("plain string"), true)
})

test("resourceConfig installs the rejection guard on window", () => {
	const config = readFileSync(new URL("../resourceConfig.js", import.meta.url), "utf8")
	assert.match(
		config,
		/addEventListener\(\s*"unhandledrejection",\s*swallowReportedRejection\s*\)/
	)
})

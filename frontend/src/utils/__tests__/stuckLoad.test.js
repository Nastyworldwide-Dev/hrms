// alpha.60: an approval sheet sat on its skeleton forever on a senior's phone
// and could not be reproduced. The stuck load reports itself to the server,
// past the app's resource fetcher (which may be the thing holding it).
// Run: cd frontend && node --test src/utils/__tests__/stuckLoad.test.js
import { test } from "node:test"
import assert from "node:assert/strict"

import { STUCK_LOAD_MS, reportStuckLoad } from "../stuckLoad.js"

test("a stuck load is posted once with what it was and whether its request was in flight", async () => {
	const calls = []
	globalThis.window = { csrf_token: "tok", location: { hostname: "h" } }
	globalThis.document = { cookie: "user_id=a%40b.c; sid=x" }
	globalThis.fetch = async (url, init) => {
		calls.push({ url, init })
		return { ok: true }
	}
	await reportStuckLoad({
		doctype: "Leave Application",
		name: "HR-LAP-1",
		ms: 10000,
		inFlight: true,
	})
	assert.equal(calls.length, 1)
	assert.equal(calls[0].url, "/api/method/hrms.api.report_stuck_load")
	assert.equal(calls[0].init.method, "POST")
	assert.equal(calls[0].init.headers["X-Frappe-CSRF-Token"], "tok")
	const body = Object.fromEntries(calls[0].init.body)
	assert.deepEqual(body, {
		doctype: "Leave Application",
		name: "HR-LAP-1",
		ms: "10000",
		in_flight: "1",
		has_user_cookie: "1",
	})
	assert.equal(STUCK_LOAD_MS, 10000)
})

test("a failed report never throws into the sheet", async () => {
	globalThis.fetch = async () => {
		throw new Error("offline")
	}
	await reportStuckLoad({ doctype: "X", name: "Y", ms: 1, inFlight: false })
})

test("the request sheet's skeleton turns into Try again and reports itself", async () => {
	const { readFileSync } = await import("node:fs")
	const { fileURLToPath } = await import("node:url")
	const src = readFileSync(
		fileURLToPath(new URL("../../components/RequestActionSheet.vue", import.meta.url)),
		"utf8"
	)
	const template = src.slice(0, src.indexOf("<script"))
	const skeleton = template.slice(template.lastIndexOf("<div v-else"))
	assert.match(skeleton, /v-if="loadIsSlow"/)
	assert.match(skeleton, /__\("Taking longer than usual\."\)/)
	assert.match(skeleton, /@click="retryLoad"/)
	assert.match(src, /setTimeout\([\s\S]*reportStuckLoad\(/)
	assert.match(src, /onBeforeUnmount\(\(\) => clearTimeout\(slowTimer\)\)/)
})

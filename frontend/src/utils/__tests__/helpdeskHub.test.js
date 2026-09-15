// The merged Helpdesk page: which pill opens, from URL, memory or default.
import { test } from "node:test"
import assert from "node:assert/strict"

import {
	DEFAULT_TAB,
	HUB_PATH,
	HUB_TABS,
	hubLocation,
	parseTab,
	resolveTab,
} from "../helpdeskHub.js"

test("the pills are HR Issues first, IT Helpdesk second", () => {
	assert.deepEqual(HUB_TABS, ["hr", "it"])
	assert.equal(DEFAULT_TAB, "hr")
})

test("parseTab accepts only a known pill", () => {
	assert.equal(parseTab("hr"), "hr")
	assert.equal(parseTab("it"), "it")
	assert.equal(parseTab("IT"), null, "case is not normalised — the URL is written by us")
	assert.equal(parseTab("tickets"), null)
	assert.equal(parseTab(undefined), null)
	assert.equal(parseTab(["hr", "it"]), null, "a repeated ?tab= is not a pill")
})

test("resolveTab: query, then remembered pill, then HR Issues", () => {
	assert.equal(resolveTab("it", "hr"), "it", "a deep link wins over memory")
	assert.equal(resolveTab(undefined, "it"), "it", "a bare visit reopens the last pill")
	assert.equal(resolveTab("bogus", "it"), "it", "junk in the URL falls through to memory")
	assert.equal(resolveTab(undefined, undefined), "hr")
	assert.equal(resolveTab(undefined, "junk"), "hr", "junk in storage falls through to default")
})

test("hubLocation targets the hub path with the pill in the query", () => {
	assert.deepEqual(hubLocation("it"), { path: HUB_PATH, query: { tab: "it" } })
})

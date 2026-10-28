import assert from "node:assert/strict"
import { test } from "node:test"
import { readFileSync } from "node:fs"

test("OrgChart.vue calls hrms.api.org_chart.get_node", () => {
	const source = readFileSync(new URL("../OrgChart.vue", import.meta.url), "utf8")
	assert.match(
		source,
		/url:\s*"hrms\.api\.org_chart\.get_node"/,
		"should call the server endpoint"
	)
	assert.match(source, /createResource/, "should use createResource")
})

test("OrgChart.vue has router.push for employee navigation", () => {
	const source = readFileSync(new URL("../OrgChart.vue", import.meta.url), "utf8")
	assert.match(source, /router\.push.*employee/, "should push route with employee param")
})

test("OrgChart.vue contains 'Away today' chip", () => {
	const source = readFileSync(new URL("../OrgChart.vue", import.meta.url), "utf8")
	assert.match(source, /Away today/, "should display Away today status")
})

test("OrgChart.vue does not reference leave_type", () => {
	const source = readFileSync(new URL("../OrgChart.vue", import.meta.url), "utf8")
	assert.doesNotMatch(source, /leave_type/, "should not mention leave_type")
})

test("Route OrgChart exists in router", () => {
	const source = readFileSync(new URL("../../router/index.js", import.meta.url), "utf8")
	assert.match(source, /path:\s*["']\/org-chart["']/, "should have /org-chart route")
	assert.match(source, /name:\s*["']OrgChart["']/, "should have OrgChart name")
})

test("More.vue has Org chart entry", () => {
	const source = readFileSync(new URL("../More.vue", import.meta.url), "utf8")
	assert.match(source, /Org chart|OrgChart/, "should mention Org chart")
	assert.match(source, /\/org-chart/, "should route to /org-chart")
})

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

test("More.vue has Organizational Chart entry", () => {
	const source = readFileSync(new URL("../More.vue", import.meta.url), "utf8")
	assert.match(source, /Organizational Chart/, "should say Organizational Chart")
	assert.match(source, /\/org-chart/, "should route to /org-chart")
})

const src = () => readFileSync(new URL("../OrgChart.vue", import.meta.url), "utf8")
const template = () => src().slice(0, src().indexOf("<script setup>"))

test("template never reads .value (refs unwrap there)", () => {
	assert.doesNotMatch(template(), /\.value\b/)
})

test("search empty copy speaks of the view, not a company", () => {
	assert.match(template(), /in this view/)
	assert.doesNotMatch(template(), /any company|your company/)
	assert.doesNotMatch(template(), /slice\(0, 8\)/)
})

test("You button is hidden, not disabled, when already on yourself", () => {
	assert.match(template(), /v-if="!isSearching && !isOnSelf"/)
	assert.doesNotMatch(src(), /aria-disabled/)
})

test("HR gap links say who they fix, and expanders declare what they control", () => {
	assert.match(template(), /__\('Fix \{0\} in Desk', \[item\.name\]\)/)
	assert.match(template(), /aria-controls="oc-gaps-detail"/)
	assert.match(template(), /aria-controls="oc-team-list"/)
	assert.match(template(), /aria-controls="oc-peers-list"/)
})

test("flow chart only: boxes, no list view and no view switch", () => {
	const t = template()
	assert.match(t, /class="oc-flow"/)
	assert.match(t, /class="oc-node oc-node--focus"/)
	assert.match(t, /class="oc-kids"/)
	assert.doesNotMatch(t, /oc-focus-card|Reports to section/)
	assert.doesNotMatch(src(), /viewMode|ui\.view|List \(earlier/)
})

test("the chain is a ladder: N more above, then the direct manager", () => {
	const t = template()
	assert.match(t, /__\("\{0\} more above", \[ladder\.above\.length\]\)/)
	assert.match(t, /__\("Direct manager"\)/)
	assert.match(t, /aria-controls="oc-above-list"/)
})

test("empty is said once: no team chip, a dashed No team yet box", () => {
	const t = template()
	assert.doesNotMatch(t, /__\("No team"\)|No one reports to/)
	assert.doesNotMatch(t, /class="oc-chip">\s*\{\{[^}]*Team of/)
	assert.match(t, /__\("No team yet"\)/)
	assert.match(t, /__\("No manager set yet"\)/)
})

test("every person in the chart uses the two-letter badge", () => {
	const avatars = template().match(/<GAvatar[^>]*>/g) || []
	assert.ok(avatars.length >= 5)
	for (const a of avatars) assert.match(a, /\bbadge\b/, a)
})

test("boxes are outlined black in light and lime in dark, focus thicker, from tokens", () => {
	const style = src().slice(src().indexOf("<style scoped>"))
	assert.match(style, /--oc-box-line:\s*var\(--g-ink\)/)
	const theme = readFileSync(new URL("../../theme/glass-components.css", import.meta.url), "utf8")
	assert.match(theme, /html\[data-theme="dark"\] \.oc-flow\s*\{[^}]*--oc-box-line:\s*var\(--g-accent-ink\)/)
	assert.match(style, /\.oc-node--focus\s*\{[^}]*box-shadow:\s*inset 0 0 0 3px var\(--oc-box-line\)/)
})

test("no scoped copy of shared glass classes, no undefined tokens", () => {
	const style = src().slice(src().indexOf("<style scoped>"))
	assert.doesNotMatch(style, /^\.g-/m)
	assert.doesNotMatch(style, /--g-warn-bg|--g-leave-bg|--g-leave-dot|cubic-bezier/)
})

test("gap group title says 'Manager has left' with proper styling", () => {
	const source = src()
	assert.match(source, /__\("Manager has left"\)/, "should say 'Manager has left'")
	// Check .oc-gap-h styling
	const style = source.slice(source.indexOf("<style scoped>"))
	assert.match(style, /\.oc-gap-h\s*{[\s\S]*?font-size:\s*0\.75rem/)
	assert.match(style, /\.oc-gap-h\s*{[\s\S]*?font-weight:\s*600/)
})

test("Fix in Desk link has ExternalLink icon", () => {
	const template = src().slice(0, src().indexOf("<script setup>"))
	assert.match(template, /ExternalLink/, "should use ExternalLink icon")
	assert.match(template, /class="w-3\.5 h-3\.5"/, "icon should be 3.5 size")
	assert.match(template, /aria-hidden="true"/, "icon should be aria-hidden")
	assert.match(template, /__\('Fix \{0\} in Desk', \[item\.name\]\)/, "link text should say 'Fix in Desk'")
})

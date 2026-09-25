// alpha.9 R1 "everything in a group" (measured by e2e/ios-consistency-audit.mjs,
// rule 8): only section headers and footers sit outside a group, as in iOS
// Settings. D3 Notifications, D4 Who to ask, D9 You.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("D4 Who to ask: an empty answer is a row in the group, under its header", () => {
	const src = read("../WhoToAsk.vue")
	assert.match(src, /<h2 class="g-form-section__title">\{\{ __\("Your manager"\) \}\}<\/h2>/)
	assert.match(src, /<h2 class="g-form-section__title">\{\{ __\("HR"\) \}\}<\/h2>/)
	assert.match(src, /<GListRow :label="NO_MANAGER" :tappable="false" \/>/)
	assert.match(src, /<GListRow :label="NO_HR" :tappable="false" \/>/)
	assert.match(src, /const NO_MANAGER = __\("No manager is set for you\."\)/)
	assert.match(src, /const NO_HR = __\("HR hasn't listed contacts yet\."\)/)
	assert.doesNotMatch(src, /g-empty-line|class="g-eyebrow/)
})

test("D3 Notifications: the unread count is the section header, not a loose line", () => {
	const src = read("../../views/Notifications.vue")
	assert.doesNotMatch(src, /<span v-if="unreadNotificationsCount\.data" class="text-caption/)
	assert.match(src, /class="g-form-section__title[^"]*">\s*\{\{ groupTitle\(group\) \}\}/)
})

test("D9 You: the version is the last group's footer", () => {
	const src = read("../../views/Profile.vue")
	assert.doesNotMatch(src, /<p class="text-caption text-ink-600 text-center">/)
	assert.match(src, /<p class="g-form-footer g-form-footer--center">\s*\{\{ __\("Version \{0\} · \{1\}"/)
})

test("D7 Overtime: why there is nothing to claim is a row in the day group", () => {
	const src = read("../../views/ot/OTRequestForm.vue")
	assert.doesNotMatch(src, /class="g-empty-line mx-4/)
	assert.match(src, /<p class="g-form-row g-form-row--stacked g-ot-empty" role="status">\s*\{\{ emptyReason \}\}/)
})

test("D8 Expense: items are rows in one group, the total is the footer", () => {
	const src = read("../ExpensesTable.vue")
	assert.doesNotMatch(src, /class="text-base font-bold text-inkbase"/, "no loose bold total in a header row")
	assert.doesNotMatch(src, /g-lineitems__row/)
	assert.match(src, /<GListRow\s+v-for="\(item, idx\) in expenseClaim\.expenses"[\s\S]*?:amount="formatCurrency\(item\.amount/)
	assert.match(src, /<p v-if="expenseClaim\.expenses\?\.length" class="g-form-footer">\s*\{\{ __\("Total \{0\}"/)
})

test("D2 Team: the day is a section header, each department a grouped section", () => {
	const src = read("../../views/team/TeamDashboard.vue")
	assert.match(src, /<h2 class="g-form-section__title" data-visual-mask>\s*\{\{ dayLabel \}\}/)
	assert.doesNotMatch(src, /g-datenav__label/)
	assert.doesNotMatch(src, /border-t-2 border-divider/, "no hand-ruled table")
	assert.match(src, /<section\s+v-for="group in departmentGroups"[\s\S]*?<div class="g-form-group">\s*<div\s+v-for="member in group\.members"/)
	assert.match(src, /<p class="g-form-footer" v-if="teamStatus\.data\?\.members\?\.length">/)
})

test("D18 one radius: the Today card and the calendar are groups (26)", () => {
	const css = read("../../theme/glass-components.css")
	assert.match(css, /\.g-cal \{[^}]*border-radius: var\(--g-radius-group\);/)
	assert.match(css, /\.g-today \{[^}]*border-radius: var\(--g-radius-group\);/)
})

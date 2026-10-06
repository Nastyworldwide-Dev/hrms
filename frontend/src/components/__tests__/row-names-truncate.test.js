// B3 (alpha.37): a long Malaysian name or a long reason broke list rows at 360 px --
// the title wrapped to three lines, or pushed the status chip off the row.
// A row's title/reason line is ONE line with an ellipsis; the full text stays
// reachable (title= for a pointer, and it is still in the DOM for a screen reader,
// since truncation is CSS only). Source-asserted: the node runner does not
// compile SFCs; the 360 px measurement is the Playwright check.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const read = (p) => readFileSync(new URL(p, import.meta.url), "utf8")
// every match of `re` (made global here, so a caller cannot forget the flag)
const tags = (src, re) => [...src.matchAll(new RegExp(re.source, "g"))].map((m) => m[0])
const classOf = (tag) => (tag.match(/\bclass="([^"]*)"/) || ["", ""])[1].split(/\s+/)

test("GListRow: the label is one line with an ellipsis, and carries its full text", () => {
	const row = read("../glass/GListRow.vue")
	const [label] = tags(row, /<span\b[^>]*g-row__label[^>]*>/g)
	assert.ok(label, "the label element exists")
	assert.ok(classOf(label).includes("truncate"), "label has truncate")
	assert.ok(classOf(label).includes("min-w-0"), "label has min-w-0")
	assert.match(label, /:title="label"/, "the full text is in title=")
})

const ITEMS = [
	"LeaveRequestItem",
	"AttendanceRequestItem",
	"ExpenseClaimItem",
	"OTRequestItem",
	"ReplacementLeaveClaimItem",
	"ShiftRequestItem",
	"ShiftAssignmentItem",
]

for (const name of ITEMS) {
	test(`${name}: the title line is one line with an ellipsis, in a column that may shrink`, () => {
		const src = read(`../${name}.vue`)
		const tpl = src.slice(0, src.indexOf("</template>\n\n<script"))
		const column = tags(tpl, /<div class="[^"]*flex flex-col[^"]*">/)[0]
		assert.ok(column, "the text column exists")
		assert.ok(classOf(column).includes("min-w-0"), "the column has min-w-0")
		assert.ok(classOf(column).includes("max-w-full"), "the column is capped at the row's width")
		const title = tags(tpl, /<div\s+class="[^"]*text-button-label[^"]*"[^>]*>/)[0]
		assert.ok(title, "the title line exists")
		assert.ok(classOf(title).includes("truncate"), "the title has truncate")
		assert.match(title, /:title="[^"]+"/, "the full text is in title=")
	})
}

test("ListItem: the text side may shrink, the status side may not, a team name is one line", () => {
	const src = read("../ListItem.vue")
	const tpl = src.slice(0, src.indexOf("<script"))
	const left = tags(tpl, /<div class="[^"]*">\s*(?=<slot name="left")/g)[0]
	assert.ok(classOf(left).includes("min-w-0"), "left has min-w-0")
	const right = tags(tpl, /<div class="[^"]*">\s*(?=<slot name="right")/g)[0]
	assert.ok(classOf(right).includes("flex-none"), "right (the status chip) does not shrink")
	const who = tags(tpl, /<div class="[^"]*text-ink-600[^"]*"[^>]*>/)[0]
	assert.ok(classOf(who).includes("truncate"), "the team member's name is one line")
	assert.ok(classOf(who).includes("min-w-0"), "and may shrink")
})

test("Team: a member's name is one line with an ellipsis and keeps its full text", () => {
	const css = read("../../theme/glass-components.css").replace(/\/\*[\s\S]*?\*\//g, "")
	const rule = css.slice(
		css.indexOf("\n.g-team-row__name {"),
		css.indexOf("}", css.indexOf("\n.g-team-row__name {"))
	)
	assert.match(rule, /overflow: hidden;/)
	assert.match(rule, /text-overflow: ellipsis;/)
	assert.match(rule, /white-space: nowrap;/)
	assert.match(
		read("../../views/team/TeamDashboard.vue"),
		/class="g-team-row__name"\s+:title="member\.employee_name"/
	)
})

test("a row that IS a sentence (an empty-state line) opts out with `wrap`: it is never cut", () => {
	const row = read("../glass/GListRow.vue")
	assert.match(row, /wrap: \{ type: Boolean, default: false \}/)
	assert.match(row, /'whitespace-normal': wrap/)
	for (const [file, sentence] of [
		["../../views/Approvals.vue", "Nothing is waiting on you."],
		["../DaySheet.vue", "You didn\\'t check in this day."],
		["../HolidayList.vue", "No public holidays ahead are listed yet."],
		["../WhoToAsk.vue", ':label="NO_MANAGER"'],
		["../WhoToAsk.vue", ':label="NO_HR"'],
	]) {
		const src = read(file)
		const at = src.indexOf(sentence)
		assert.ok(at > 0, `${sentence} found in ${file}`)
		const tag = src.slice(src.lastIndexOf("<GListRow", at), src.indexOf("/>", at) + 2)
		const tagEnd = src.slice(at, src.indexOf(">", at))
		assert.match(tag + tagEnd, /\bwrap\b/, `${sentence} keeps wrapping`)
	}
})

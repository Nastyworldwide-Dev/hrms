// The Approvals page's filter, select mode, banner and bulk approve are WIRED to the helpers
// (utils/approvalBulk.js) and to the two server endpoints (hrms.api.approval.check_many /
// decide_many). The helpers have their own tests; this keeps the page from drifting off them.
// HR, 4 Oct 2026; owner, 5 Oct: no export, banner only, phone and desktop. Owner rulings 8 Oct 2026:
// only the approver's own requests, ticks always shown (no Select mode), bulk reject, up to 100.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const page = readFileSync(fileURLToPath(new URL("../Approvals.vue", import.meta.url)), "utf8")
const template = page.slice(0, page.indexOf("<script"))
const script = page.slice(page.indexOf("<script"), page.indexOf("<style"))

test("it calls the three bulk endpoints, and nothing else decides in bulk", () => {
	assert.match(script, /hrms\.api\.approval\.check_many/)
	assert.match(script, /hrms\.api\.approval\.decide_many/)
	// 8 Oct 2026 (owner): bulk reject overrides the 5 Oct "reject one by one"; it still goes through
	// the server's own endpoint, never a status written from the page
	assert.match(script, /hrms\.api\.approval\.reject_many/)
	assert.doesNotMatch(
		script,
		/status:\s*["']Rejected["']/,
		"the page never writes a status itself"
	)
})

test("the filter narrows the groups, so every count follows it", () => {
	// 8 Oct 2026: type, department, employee and dates are one pure filterRows (was filterByKind alone)
	assert.match(script, /filterRows\(rows\.value, \{ kind: kindFilter\.value, \.\.\.filters \}\)/)
	assert.match(script, /groupApprovals\(visibleRows\.value\)/)
	assert.match(template, /aria-pressed/, "a chip says whether it is on")
})

test("what is sent is the ticked rows that are SHOWN, with the revision the approver saw", () => {
	assert.match(script, /itemsFor\(ticked\.value, visibleRows\.value\)/)
})

test("only what the check said would go through is approved, ten at a time", () => {
	// 8 Oct 2026 (owner): up to 100 per action; the server takes 50 per call, so ten per call
	assert.match(
		script,
		/sendInChunks\(\s*current\.ready,\s*\(part\) => decideMany\.submit\(\{ items: part \}\),\s*"approved"/
	)
	// the check is chunked too: check_many refuses a call over the server's cap of 50
	assert.match(
		script,
		/sendInChunks\(\s*items,\s*\(part\) => checkMany\.submit\(\{ items: part \}\),\s*"ready"/
	)
})

test("the confirm sheet says ready and refused, with the reason, and refused ones stay", () => {
	assert.match(template, /__\("\{0\} ready"/)
	assert.match(template, /__\("\{0\} will be refused"/)
	assert.match(template, /:sublabel="req\.reason"/)
	assert.match(template, /Refused ones stay in your list/)
})

test("over the cap is caught before the server is asked, for approve and reject alike", () => {
	assert.equal((script.match(/overCap\(ticked\.value\)/g) || []).length, 2)
	// 8 Oct 2026: the words carry the cap from the helper (100), not a number typed here
	assert.match(script, /__\("Pick up to \{0\} at a time", \[BULK_CAP\]\)/)
	assert.doesNotMatch(script, /up to 50/i)
})

test("a check-in is never ticked: ticks are drawn only on what can be decided in bulk", () => {
	// 8 Oct 2026 (owner): there is no Select mode any more; the same canBulk rule decides the tick
	assert.match(template, /person\.rows\.some\(canBulk\)/)
	assert.match(script, /pickable = computed\(\(\) => visibleRows\.value\.filter\(canBulk\)\)/)
})

test("the banner is a banner: it blocks nothing and forces nothing", () => {
	assert.match(template, /<GBanner v-if="headline"/)
	assert.match(template, /Staff attendance and pay wait on your decision/)
	assert.doesNotMatch(template, /overdue-gate|mandatory|blocking/i)
})

test("an age is a number AND a word, never colour alone", () => {
	assert.match(script, /__\("Today"\)/)
	assert.match(script, /__\("\{0\} days", \[days\]\)/)
})

test("the open-request sheet and the ticked set are different things", () => {
	assert.match(script, /const ticked = ref\(new Set\(\)\)/)
	assert.match(script, /const selected = ref\(null\)/)
})

test("there is no export", () => {
	assert.doesNotMatch(page, /export(?!\s+(default|const|function|async))[^\n]*(csv|excel|xlsx)/i)
	assert.doesNotMatch(template, />\s*Export\s*</)
})

test("the sticky bar names how many and checks first", () => {
	assert.match(template, /__\("\{0\} selected"/)
	assert.match(template, /Each one is checked before it is approved/)
})

test("the bar has Clear, Reject and Approve (owner ruling 8 Oct 2026)", () => {
	const bar = template.slice(template.indexOf('class="g-approvals__bar"'))
	const end = bar.slice(0, bar.indexOf("</div>\n\n"))
	assert.match(end, /__\("Clear"\)/)
	assert.match(
		end,
		/<GButton[^>]*danger[^>]*:label="__\('Reject'\)"[\s\S]*@click="startReject"|<GButton[^>]*:label="__\('Reject'\)"[^>]*danger[^>]*@click="startReject"/
	)
	assert.match(end, /<GButton[^>]*:label="__\('Approve'\)"[^>]*@click="startApprove"/)
	// it shows the moment something is ticked: no Select mode to turn on first
	assert.match(template, /v-if="ticked\.size"\s+class="g-approvals__bar"/)
})

test("the empty line shows only when nothing waits, never above a queue", () => {
	// it hung off a v-else; inserting the select-all row between the pair moved the else
	const at = template.indexOf("Nothing is waiting on you")
	const opening = template.lastIndexOf("<GListPanel", at)
	assert.match(template.slice(opening, at), /^<GListPanel v-if="!rows\.length"/)
	assert.doesNotMatch(
		template,
		/<GListPanel v-else>\s*<GListRow\s+:label="__\('Nothing is waiting on you/
	)
})

test("the chip that is on has readable colours: both come from tokens that exist", () => {
	const style = page.slice(page.indexOf("<style"))
	const on = style.slice(style.indexOf(".g-approvals__chip--on"))
	const rule = on.slice(0, on.indexOf("}"))
	for (const token of rule.match(/var\((--g-[a-z0-9-]+)\)/g) || []) {
		const name = token.slice(4, -1)
		const defined = readFileSync(
			fileURLToPath(new URL("../../theme/glass.css", import.meta.url)),
			"utf8"
		)
		assert.ok(defined.includes(`${name}:`), `${name} is not defined in the theme`)
	}
})

test("ages and the banner count from the site's calendar day, never the UTC date", () => {
	assert.match(script, /siteToday\(new Date\(\), siteTimeZone\(\)\)/)
	assert.doesNotMatch(script, /toISOString\(\)\.slice\(0, 10\)/)
})

test("ticks follow the filter: one that is no longer shown is dropped before it can be sent", () => {
	assert.match(
		script,
		/watch\(visibleRows, \(list\) => \(ticked\.value = keepVisible\(ticked\.value, list\)\)\)/
	)
})

test("a failure stays in the sheet with the ticks kept and a way to try again", () => {
	assert.match(template, /sheet\.phase === 'failed'/)
	assert.match(template, /__\(["']Try again["']\)/)
	assert.doesNotMatch(
		script,
		/Could not check these/,
		"no toast that disappears and leaves nothing to press"
	)
})

test("a filter with nothing tickable says why", () => {
	// 8 Oct 2026: no Select mode, so the line shows whenever only check-ins are left
	assert.match(template, /v-if="nothingTickable\(visibleRows\)"/)
	assert.match(template, /approved one by one/)
})

test("the sticky bar sits above the floating tab bar and the home indicator, never under them", () => {
	// position: sticky; bottom: 0 sticks to the scrollport edge, which the tab bar overlays. The
	// reservation lives in ion-content's --padding-bottom (theme/glass-components.css); the bar
	// reads the same value, and never less than the safe area on a page with no tab bar.
	const style = page.slice(page.indexOf("<style"))
	const bar = style.slice(style.indexOf(".g-approvals__bar {"))
	const rule = bar.slice(0, bar.indexOf("}"))
	assert.match(
		rule,
		/bottom:\s*max\(var\(--padding-bottom, 0px\), env\(safe-area-inset-bottom, 0px\)\)/
	)
	assert.doesNotMatch(rule, /bottom:\s*0\b/)
})

test("the last row is never covered by the bar: the list gets room while the bar shows", () => {
	assert.match(template, /g-approvals__page--barred/)
	assert.match(
		page.slice(page.indexOf("<style")),
		/\.g-approvals__page--barred\s*\{[^}]*padding-bottom/
	)
})

test("the age badge passes 4.5:1 on the page colour in the light theme: ink alone, no tint", () => {
	// measured 5 Oct 2026: amber #B24A00 and red #D70015 on --g-bg #F2F2F7 are 4.86 / 4.83 as plain
	// text but 4.37 / 4.20 on an 8% tint of themselves. The words (a number of days) carry the meaning.
	const style = page.slice(page.indexOf("<style"))
	for (const tone of ["amber", "red"]) {
		const at = style.indexOf(`.g-approvals__age--${tone}`)
		const rule = style.slice(at, style.indexOf("}", at))
		assert.doesNotMatch(
			rule,
			/background:\s*rgb\(/,
			`${tone} badge must not sit on a tint of itself`
		)
	}
})

test("a failed APPROVE does not claim nothing was approved: the server may have got some through", () => {
	// only a failed CHECK writes nothing; a timeout after decide_many may have approved some
	assert.match(template, /sheet\.phase === 'failed-approve'/)
	assert.match(template, /could not confirm/i)
	const check = script.slice(
		script.indexOf("async function startApprove"),
		script.indexOf("async function confirmApprove")
	)
	const approve = script.slice(
		script.indexOf("async function confirmApprove"),
		script.indexOf("function startReject")
	)
	assert.match(check, /phase: "failed"/)
	// 8 Oct 2026: approve and reject share ONE failure path (failedWrite) instead of two copies
	assert.match(approve, /failedWrite\("failed-approve"/)
	assert.doesNotMatch(approve, /phase: "failed"[^-]/)
})

test("a failed REJECT says the same: what went through is unknown, the list reloads, the ticks stay", () => {
	// 8 Oct 2026 (owner): a chunk that throws stops the rest, and the page cannot know how many of the
	// earlier chunks were written
	// confirmReject up to the end of the shared failure path
	const reject = script.slice(
		script.indexOf("async function confirmReject"),
		script.indexOf("async function refresh")
	)
	assert.match(reject, /failedWrite\("failed-reject"/)
	assert.match(reject, /phase: "failed-reject"|phase === "failed-reject"/)
	assert.match(reject, /try \{\s*await waiting\.reload\(\)\s*\} catch/)
	assert.match(template, /sheet\.phase === 'failed-reject'/)
	assert.match(template, /__\("We could not confirm what was rejected\."\)/)
})

test("a reload that throws while reporting a failure is handled, not left to crash the page", () => {
	// the one shared failure path (failedWrite), used by approve and reject alike
	const approve = script.slice(
		script.indexOf("async function failedWrite"),
		script.indexOf("async function refresh")
	)
	assert.match(approve, /try \{\s*await waiting\.reload\(\)\s*\} catch/)
})

test("the sheet cannot be closed under a working request: the modal itself refuses", () => {
	// the refusal lives in GModal (dismissible), not in a handler that ignores did-dismiss: Ionic
	// has already closed the overlay by then and the sheet is never re-presented
	assert.match(template, /:dismissible="sheet\?\.phase !== 'working'"/)
	assert.doesNotMatch(script, /dismissSheet/)
})

test("no dead field on the sheet object", () => {
	assert.doesNotMatch(script, /retry:\s*startApprove/)
})

// ---- bulk v2 (owner rulings 8 Oct 2026) ----

test("there is no Select button and no select mode: ticks are always shown on tickable rows", () => {
	// 4 taps: type chip, Select all, Approve, Confirm
	assert.doesNotMatch(script, /selectMode|toggleSelectMode/)
	assert.doesNotMatch(template, /selectMode|toggleSelectMode|__\("Select"\)|__\("Done"\)/)
	assert.match(template, /v-if="pickable\.length"/)
	assert.match(template, /__\(['"]Select all \{0\}['"], \[pickable\.length\]\)/)
	assert.match(template, /toggleAll\(ticked, visibleRows\)/)
})

test("the page lists only the approver's own requests: Other teams and its fold are gone", () => {
	// the ruling is quoted in comments; the code and the words on screen must not carry it
	const live = page.replace(/<!--[\s\S]*?-->/g, "").replace(/\/\/[^\n]*/g, "")
	assert.doesNotMatch(live, /Other teams|otherOpen|approvals-other-teams|g-approvals__toggle/)
	assert.match(script, /onlyYours\(waiting\.data\?\.rows \|\| \[\]\)/)
})

test("a tickable row has a tick of its own AND a body that opens the request", () => {
	// without Select mode a tap on the row can no longer mean "tick", or no request could be opened
	// to read its reason or file; the tick is its own 44 pt control, the text opens the sheet
	assert.match(template, /role="checkbox"[\s\S]*@click="ticked = toggle\(ticked, req\)"/)
	assert.match(template, /g-approvals__reqbody[\s\S]*@click="open\(req\)"/)
	assert.doesNotMatch(
		template,
		/<GListRow[^>]*role="checkbox"/,
		"no checkbox nested in a row button"
	)
})

test("the row line carries the details per type, the label keeps the name and dates", () => {
	assert.match(template, /:sublabel="rowDetails\(req, __\)"/)
	assert.match(script, /`\$\{row\.who\} · \$\{row\.when\}`|\[row\.who, row\.when\]/)
})

test("chips read label (count) and the oldest request stays first", () => {
	assert.match(template, /chipLabel\(chip, __\)/)
	assert.doesNotMatch(
		template,
		/\{\{ chip\.key \? __\(chip\.label\) : __\("All"\) \}\} · \{\{ chip\.count \}\}/
	)
})

test("Filter opens one sheet: department, employee, and a date range; the button counts what is on", () => {
	assert.match(template, /__\("Filter \(\{0\}\)", \[filterCount\]\)/)
	assert.match(script, /activeFilters\(filters\)/)
	const sheet = template.slice(template.indexOf(":title=\"__('Filter')\""))
	const filterSheet = sheet.slice(0, sheet.indexOf("</GModal>"))
	assert.match(filterSheet, /<GSelect[\s\S]*v-model="filters\.department"/)
	assert.match(filterSheet, /<GSelect[\s\S]*v-model="filters\.employee"/)
	assert.match(filterSheet, /<GDatePicker[\s\S]*v-model="filters\.from"/)
	assert.match(filterSheet, /<GDatePicker[\s\S]*v-model="filters\.to"/)
	assert.match(filterSheet, /__\("Dates"\)/)
	assert.match(filterSheet, /__\(['"]Clear['"]\)/)
	assert.match(script, /departmentOptions\(rows\.value\)/)
	assert.match(script, /employeeOptions\(/)
})

test("a filter that hides everything says so, and a vanished department or employee is dropped", () => {
	assert.match(template, /v-if="rows\.length && !visibleRows\.length"/)
	assert.match(script, /pruneFilters\(/)
})

test("Approve keeps the check sheet: titled with the count, a one-line summary, then ready and refused", () => {
	assert.match(script, /__\("Approve \{0\} requests\?", \[/)
	assert.match(script, /__\("Approve 1 request\?"\)/)
	assert.match(script, /summary: kindSummary\(/)
	const ready = template.indexOf('__("{0} ready"')
	assert.ok(template.indexOf("{{ sheet.summary }}") < ready, "the summary sits above the lists")
})

test("Reject: titled with the count, one shared reason that is required, an Edit reason per request", () => {
	assert.match(script, /__\("Reject \{0\} requests\?", \[/)
	assert.match(script, /__\("Reject 1 request\?"\)/)
	assert.match(
		template,
		/<GTextarea[\s\S]*v-model="rejectShared"[\s\S]*__\('Why not\? \(required\)'\)|<GTextarea[\s\S]*:label="__\('Why not\? \(required\)'\)"[\s\S]*v-model="rejectShared"/
	)
	assert.match(template, /__\("Edit reason"\)/)
	// the disclosure says whether it is open, and points at the field it opens
	assert.match(template, /:aria-expanded="String\(Boolean\(rejectEditing\[rowKey\(req\)\]\)\)"/)
	assert.match(template, /:aria-controls="`approvals-reason-\$\{/)
	// an own reason starts empty: empty means "use the shared one"
	assert.match(script, /const rejectOwn = reactive\(\{\}\)/)
})

test("the Reject button stays off until every request has a reason, and sends them per row", () => {
	assert.match(template, /:disabled="!rejectReady"/)
	assert.match(script, /const rejectReady = computed\(/)
	assert.match(script, /canReject\(sheet\.value\.items, rejectShared\.value, rejectOwn\)/)
	assert.match(script, /rejectItems\(/)
	assert.match(
		script,
		/sendInChunks\(\s*items,\s*\(part\) => rejectMany\.submit\(\{ items: part, reason: sharedFor\(part, rejectShared\.value\) \}\),\s*"rejected"/
	)
})

test("the work says how far it is: 'Approving 30 of 100…' and 'Rejecting …', polite and announced", () => {
	assert.match(script, /__\("Approving \{0\} of \{1\}…"/)
	assert.match(script, /__\("Rejecting \{0\} of \{1\}…"/)
	assert.match(
		template,
		/role="status"[^>]*aria-live="polite"|aria-live="polite"[^>]*role="status"/
	)
	assert.match(template, /\{\{ progressText \}\}/)
})

test("when some are refused the sheet stays open: '{n} not approved', each with its name and reason", () => {
	assert.match(template, /sheet\.phase === 'result'/)
	assert.match(template, /__\("\{0\} not approved", \[sheet\.refused\.length\]\)/)
	assert.match(template, /__\("\{0\} not rejected", \[sheet\.refused\.length\]\)/)
	// the toast still says how many went through; refused stay ticked (afterApprove keeps them)
	assert.match(script, /__\("\{0\} rejected", \[/)
	assert.match(script, /afterApprove\(ticked\.value, /)
})

test("a long label wraps and keeps the dates; the page bar clears the taller bar", () => {
	assert.match(template, /class="g-approvals__reqbody"\s+:label="reqLabel\(req\)"\s+wrap/)
	assert.match(
		page.slice(page.indexOf("<style")),
		/\.g-approvals__page--barred\s*\{[^}]*padding-bottom: 136px/
	)
})

test("each control is told apart by a screen reader (design review of b47084495)", () => {
	// a tick names the kind: two requests of one person on one date must not sound the same
	assert.match(template, /role="checkbox"[\s\S]{0,200}:aria-label="rowLabel\(req\)"/)
	// the two Clear buttons say what they clear
	assert.match(template, /__\('Clear filters'\)/)
	assert.match(template, /__\('Clear selection'\)/)
	// every "Edit reason" names its person
	assert.match(template, /__\('Edit reason for \{0\}', \[req\.who\]\)/)
	// a disabled Reject says why, on screen, and is described by it
	assert.match(template, /id="approvals-reject-hint"[\s\S]{0,120}Add a reason to continue\./)
	assert.match(template, /:aria-describedby="rejectReady \? undefined : 'approvals-reject-hint'"/)
})

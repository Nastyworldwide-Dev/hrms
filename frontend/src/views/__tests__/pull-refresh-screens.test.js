// Pull down to refresh on the screens that lacked it (6 Oct 2026, alpha.35). A person pulled Notifications,
// Team, the roster, Calendar, Time off and Help and nothing happened: there was no refresher at all.
// Source-level pins, like the other tests in this directory; the REAL gesture is proved in a browser by
// e2e/pull-refresh.spec.js. Each screen must (1) draw <GPullRefresh> as the FIRST child of its scrolling
// content, (2) load it lazily, the way Home does, and (3) reload exactly what it shows, then complete.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (file) => readFileSync(fileURLToPath(new URL(`../${file}`, import.meta.url)), "utf8")

const BODY = "<template #body>"
// [file, what opens the scrolling content, the log tag, what a pull must reload]
const SCREENS = [
	[
		"Notifications.vue",
		'<ion-content class="ion-padding g-page__content">',
		"[Notifications]",
		["notifications.reload()", "unreadNotificationsCount.reload()"],
	],
	["team/TeamDashboard.vue", BODY, "[TeamDashboard]", ["teamStatus.reload()", "teamManagers.reload()"]],
	["team/TeamRoster.vue", BODY, "[TeamRoster]", ["teamRoster.reload()", "teamManagers.reload()"]],
	[
		"attendance/Dashboard.vue",
		BODY,
		"[AttendanceDashboard]",
		["calendar.value?.refresh?.()", "monthFlags.reload()", "shifts.reload()"],
	],
	["leave/Dashboard.vue", BODY, "[LeaveDashboard]", ["leaveBalance.reload()", "myLeaves.reload()"]],
	[
		"issues/IssueList.vue",
		'<div class="flex flex-col gap-4 px-4 pt-4 w-full max-w-content-column-lg mx-auto">',
		"[IssueList]",
		["myIssues.reload()"],
	],
	["helpdesk/HelpdeskHub.vue", BODY, "[HelpdeskHub]", ["myTickets.reload()", "helpdeskAvailable.reload()"]],
]

const refreshBody = (src) => {
	const start = src.indexOf("async function refresh(event) {")
	assert.notEqual(start, -1, "an async refresh(event)")
	return src.slice(start, src.indexOf("\n}\n", start))
}

for (const [file, opener, tag, reloads] of SCREENS) {
	test(`${file}: the pull is the first child of the scrolling content`, () => {
		const src = read(file)
		// only whitespace and comments may sit between the opener and the refresher
		const first = new RegExp(
			`${opener.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(\\s|<!--[\\s\\S]*?-->)*<GPullRefresh (v-if="[^"]+" )?@refresh="refresh" />`
		)
		assert.match(src, first)
		assert.equal((src.match(/<GPullRefresh/g) || []).length, 1, "one refresher per screen")
	})

	test(`${file}: the refresher loads lazily, as Home does`, () => {
		assert.match(
			read(file),
			/const GPullRefresh = defineAsyncComponent\(\(\) => import\("@\/components\/glass\/GPullRefresh\.vue"\)\)/
		)
	})

	test(`${file}: a pull reloads what the screen shows, then completes`, () => {
		const body = refreshBody(read(file))
		assert.ok(body.includes(`console.info("${tag} pull-to-refresh")`), "one log line")
		for (const call of reloads) assert.ok(body.includes(call), call)
		// every reload runs even if one fails, and the pull always closes
		if (reloads.some((r) => r.endsWith(".reload()"))) assert.match(body, /await Promise\.allSettled\(\[/)
		assert.match(body, /event\.target\?\.complete\?\.\(\)\s*$/)
	})
}

test("the HR and IT pills never draw two refreshers on one page", () => {
	// IssueList (HR pill) draws its own; the hub draws one only for the IT pill
	const hub = read("helpdesk/HelpdeskHub.vue")
	assert.match(hub, /<GPullRefresh v-if="tab === IT_TAB" @refresh="refresh" \/>/)
	assert.match(read("issues/IssueList.vue"), /<GPullRefresh @refresh="refresh" \/>/)
})

// The approved Home plan (docs/glass/plan/pages/02-home.md, 23 Sep 2026):
// Home answers "what is true now, and what is waiting on me". Source-asserted
// (no SFC compile in node).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8")
const home = read("../Home.vue")
const template = home.slice(0, home.indexOf("<script"))
const checkin = read("../../components/CheckInPanel.vue")
const checkinTemplate = checkin.slice(0, checkin.indexOf("<script"))

test("H1: the Requests panel is not on Home (it lives on Requests)", () => {
	assert.doesNotMatch(template, /<RequestPanel/)
})

test("H2/H3: the date is the header title, said once, not in capitals", () => {
	assert.match(template, /:page-title="todayTitle"|:pageTitle="todayTitle"/)
	assert.match(home, /format\("ddd D MMM"\)/)
	assert.doesNotMatch(checkinTemplate, /toUpperCase\(\)/)
	assert.doesNotMatch(checkinTemplate, /format\("dddd, D MMMM YYYY"\)/)
})

test("H6: the check-in history link is not on Home (it lives on Calendar)", () => {
	assert.doesNotMatch(checkinTemplate, /View your check-ins/)
})

test("H7: the notification permission sheet does not open by itself on Home", () => {
	assert.doesNotMatch(template, /<PushNotificationPrompt/)
})

test("H7: the permission ask comes after a check-in, from the check-in panel", () => {
	assert.match(checkinTemplate, /<PushNotificationPrompt v-if="askForNotifications"/)
	assert.match(checkin, /askForNotifications\.value = true/)
})

test("pulling down refreshes what Home shows: the Now bar, what waits on you, announcements", () => {
	const body = home.slice(home.indexOf("async function refresh"), home.indexOf("</script>"))
	for (const resource of ["nowResource", "needsYouResource", "pendingCountResource", "homeAnnouncements"]) {
		assert.match(body, new RegExp(`${resource}\\.reload\\(`), resource)
	}
	assert.doesNotMatch(body, /reloadRequestLists/)
})

test("on desktop the date is not said twice (the title already says it)", () => {
	const layout = read("../../components/BaseLayout.vue")
	assert.match(layout, /:kicker="props\.pageTitle \? undefined : dateKicker"/)
})

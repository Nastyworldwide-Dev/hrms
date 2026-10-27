// A day with a company event says so on its sheet (owner, 27 Oct 2026: "put any event on a
// certain day"). The server sends `events: [{name, title, summary}]` for the day, fenced by the
// announcement audience, and only when there is one; the sheet draws an "Events" group between
// the person's own day and the team, one row per event, and a tap opens the announcement.
// Read from source: no SFC compile in node.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const read = (p) => readFileSync(new URL(p, import.meta.url), "utf8")
const sheet = read("../DaySheet.vue")
const template = sheet.slice(0, sheet.indexOf("</template>\n\n<script"))

// the events <section>, from its opening tag to the first closing one
function eventsSection() {
	const at = template.indexOf("g-form-section")
	assert.ok(at >= 0)
	const start = template.indexOf('v-if="eventRows.length"')
	assert.ok(start >= 0, "the events section is drawn only when there are events")
	return template.slice(start, template.indexOf("</section>", start))
}

test("the sheet reads the day's events from the server's answer, and only when some arrived", () => {
	assert.match(sheet, /daySheet\.data\?\.events/, "reads sections.events")
	assert.match(sheet, /\|\| \[\]/, "an absent section is an empty list")
	assert.match(template, /v-if="eventRows\.length"/, "no events: nothing is drawn, not an empty state")
})

test("the Events group is a titled section holding one row per event", () => {
	const section = eventsSection()
	assert.match(section, /g-form-section__title/)
	assert.match(section, /__\("Events"\)/)
	assert.match(section, /<GListPanel>/)
	assert.match(section, /v-for="event in eventRows"/)
	assert.match(section, /:key="event\.name"/)
	assert.match(section, /:label="event\.title"/)
	assert.match(section, /:sublabel="event\.summary"/)
})

test("an event row is tappable and opens the announcement page", () => {
	const section = eventsSection()
	assert.match(section, /@click="openEvent\(event\)"/)
	assert.doesNotMatch(section, /:chevron="false"/, "a row that navigates keeps its chevron")
	assert.doesNotMatch(section, /:tappable="false"/)
	assert.match(
		sheet,
		/router\.push\(\{ name: "AnnouncementDetail", params: \{ id: event\.name \} \}\)/,
		"the route the Home card and the board use"
	)
})

test("the Events group sits after the person's own day and before the team", () => {
	const mine = template.indexOf("shiftLine")
	const events = template.indexOf('v-if="eventRows.length"')
	const team = template.indexOf('v-if="teamRows.length"')
	assert.ok(mine >= 0 && events >= 0 && team >= 0)
	assert.ok(mine < events, "after Your day")
	assert.ok(events < team, "before the team")
})

test("the route it opens exists, by that name, with the id as a prop", () => {
	const router = read("../../router/index.js")
	assert.match(router, /path: "\/announcements\/:id",\s*name: "AnnouncementDetail"/)
})

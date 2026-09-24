// The announcement board in the PWA (revamp §3, slice B2).
//
// The feature the owner asked for by name, and the one the old plan's "no new
// backend in 2.0" rule made impossible — which is why 2.0 shipped seven
// string-only slices and looked unchanged.
//
// What is pinned here is the part a later edit would break without noticing:
// the block disappears when the board is empty rather than showing a permanent
// "no announcements" card; Home is bounded at two with the rest COUNTED; the
// category never goes through __(); and the badge is a word rather than a
// colour, because §14.1 forbids colour as the only signal.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("../..", import.meta.url))
const read = (p) => readFileSync(join(SRC, p), "utf8")

function code(text) {
	return text
		.replace(/<!--[\s\S]*?-->/g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/\/\*[\s\S]*?\*\//g, (b) => b.replace(/[^\n]/g, " "))
		.replace(/(^|[^:])\/\/[^\n]*/g, (l, lead) => lead + " ".repeat(l.length - lead.length))
}

const block = code(read("components/Announcements.vue"))
const list = code(read("views/announcements/List.vue"))
const detail = code(read("views/announcements/Detail.vue"))

test("an empty board says so in one line on Home", () => {
	// SUPERSEDED 23 Sep (owner: "Home is broken top to bottom"; plan P1-1,
	// NN/g empty states): a block that vanished left Home reading as broken.
	// Once loaded, the block always shows, with "No news." when it is empty —
	// one line, not a standing card.
	assert.match(block, /v-else-if="homeAnnouncements\.data"/, "shown once loaded")
	// alpha.7 (25 Sep): the line reads "No new announcements · See all".
	assert.match(block, /__\("No new announcements"\)/, "an empty board says so")
	assert.doesNotMatch(block, /GEmptyState/, "no standing empty card on Home")
	// The full board DOES have one, because arriving at a screen that renders
	// nothing reads as broken.
	assert.match(list, /GEmptyState/, "the board itself says when it is empty")
})

test("Home shows what it has and counts what it does not", () => {
	// A count nobody can see is a decision the reader has to make blind: is it
	// worth tapping through for one more, or twelve?
	assert.match(block, /__\("See \{0\} more", \[more\]\)/, "the rest is stated as a number")
	assert.match(block, /homeAnnouncements\.data\?\.more/, "and it comes from the server")
})

test("the category is mapped, never translated", () => {
	// A doctype Select value is not in the translation files, so `__(category)`
	// renders the raw English word. The OT compensation row and the attendance
	// chip both carried exactly this defect this month.
	for (const [name, source] of [
		["Home block", block],
		["board", list],
		["detail", detail],
	]) {
		assert.doesNotMatch(source, /__\(\s*\w*\.?category\s*[,)]/, `${name} translates a wire value`)
	}
	assert.match(block, /const ICONS = \{/, "the mapping is explicit")
	assert.match(detail, /const CATEGORY_LABELS = \{/, "and so are the words")
})

test("unread and waiting are said in words, not only in colour", () => {
	// §14.1: colour may never be the only signal. A coloured dot is invisible
	// to a colour-blind reader and to a greyscale screenshot.
	assert.match(block, /__\("Confirm"\)/, "a card that wants something says so")
	assert.match(block, /__\("New"\)/, "and an unread one says that")
	assert.doesNotMatch(block, /g-dot/, "not a bare dot")
})

test("acknowledgement is a sentence, not an OK button", () => {
	// "I've read and understood this" is a statement a person makes; "OK" is a
	// dialog being dismissed. For a safety notice that is the whole feature.
	assert.match(detail, /I've read and understood this/)
	assert.match(detail, /acknowledge_required/, "and only when HR asked for it")
})

test("acknowledging refreshes both boards", () => {
	// The card leaves Home's "needs you" slot AND loses its badge on the full
	// board. Refreshing one leaves the other wrong until a full reload.
	assert.match(detail, /reloadAnnouncements\("acknowledged"\)/)
})

test("opening the detail is what marks it read", () => {
	// Fetching on every open, not only when the payload is missing: coming
	// back to re-read a policy is a read, and a cached resource would never
	// reach the server to record it.
	assert.match(detail, /announcementDetail\.fetch\(\{ name: id, preview: preview\.value \? 1 : 0 \}\)/)
	assert.match(detail, /\{ immediate: true \}/, "including the first open")
	const data = code(read("data/announcements.js"))
	const block_ = data.slice(
		data.indexOf("announcementDetail"),
		data.indexOf("acknowledgeAnnouncement")
	)
	assert.doesNotMatch(block_, /cache:/, "a cached detail would never record the read")
})

test("the boards are cached per person", () => {
	// An announcement board is audience-filtered, so a shared cache key serves
	// one employee's department notices to the next person to sign in on the
	// same device — routine on a shared factory phone.
	const data = code(read("data/announcements.js"))
	assert.equal(
		(data.match(/personalCacheKey\(/g) || []).length,
		2,
		"both boards, personally keyed"
	)
})

test("the board is inside the tab shell", () => {
	// A top-level route drops the tab bar, and Back from it leaves the app.
	const router = code(read("router/index.js"))
	const shell = router.slice(0, router.indexOf('path: "/notifications"'))
	assert.match(shell, /name: "Announcements"/, "the list is a tab child")
	assert.match(shell, /name: "AnnouncementDetail"/, "and so is the detail")
})

test("the More tab stays lit while you are on the board", () => {
	// MORE_ITEMS is computed, so the entry appears under More on its own — but
	// the tab's `routes` list is hand-kept, and a destination missing from it
	// leaves the bar with nothing selected while you stand on it.
	const nav = code(read("data/navItems.js"))
	const more = nav.slice(nav.indexOf("routes: ["), nav.indexOf("]", nav.indexOf("routes: [")))
	assert.match(more, /"\/announcements"/)
})

test("a failed read is not an empty board", () => {
	// Both rendered nothing, so a notice HR had published and an outage looked
	// identical from the sofa. Absence is the right EMPTY state; silence is
	// not the right ERROR — the same class as the Now bar hiding itself.
	assert.match(block, /v-if="homeAnnouncements\.error"/, "the error is its own branch")
	assert.ok(
		block.indexOf("homeAnnouncements.error") < block.indexOf('v-else-if="homeAnnouncements.data"'),
		"and it is checked first"
	)
	assert.match(block, /could not be loaded/, "it says so")
})

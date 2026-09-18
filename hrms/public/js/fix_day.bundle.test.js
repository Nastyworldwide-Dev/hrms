// The Fix Day screen offers the duplicate-row action only where it applies,
// and still types no result.
//
// Reported 17 Sep 2026: a day carrying two Attendance rows could not be reduced
// to one anywhere — the report shows one row, the Attendance list shows two,
// and the master edit refuses such a day outright. The sixth action closes
// that, and these pin the two things the screen must keep promising: the button
// appears only on a day that really has more than one live row, and the server
// remains the one that decides WHICH row may go.
//
// Source-asserted, like the screen's Python-side test: this bundle runs inside
// Frappe's Desk and cannot be imported here.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("./fix_day.bundle.js", import.meta.url)), "utf8")

test("the button is offered only on a day with more than one row", () => {
	assert.match(
		src,
		/duplicate_rows\(\)\s*\{[\s\S]*?rows\.length > 1 \? rows : \[\]/,
		"a one-row day has no duplicate to remove"
	)
	assert.match(
		src,
		/this\.duplicate_rows\(\)\.length \? button\("dedupe"/,
		"the button must not render on a one-row day"
	)
})

test("the action goes through the one shared run(), like every other", () => {
	assert.match(
		src,
		/this\.run\("remove_duplicate_row", \{/,
		"it must use run(), which reloads the day and shows before/after"
	)
})

test("the screen sends a row and a reason, and decides nothing itself", () => {
	const start = src.indexOf("dedupe() {")
	assert.ok(start > 0, "the action exists")
	const body = src.slice(start, src.indexOf("\n\t}", start))
	assert.match(body, /attendance:/, "the chosen row")
	assert.match(body, /reason: values\.reason/, "and why — recorded on the row and in the log")
	// Which row MAY go is the server's call (it keeps the row the punches are
	// linked to). The screen must not pre-judge it by filtering the list.
	assert.doesNotMatch(body, /linked_punches|auto_attendance|marked_by_hr/)
})

test("no control on this screen types a result", () => {
	for (const field of src.matchAll(/fieldname: "(\w+)"/g)) {
		const name = field[1].toLowerCase()
		assert.ok(!name.includes("hour"), `${field[1]} would let HR type a result`)
		assert.ok(!name.includes("ot_"), `${field[1]} would let HR type a result`)
		assert.ok(!name.includes("status"), `${field[1]} would let HR type a result`)
	}
})

// The class, not the instance. A file loaded at BOOT (hooks.app_include_js)
// cannot own a doctype's listview_settings: the doctype's own list script is
// fetched when the list opens, assigns that key outright, and whatever the
// bundle wrote is gone. That cost HR the "Fix day" button on Employee Checkin
// for a week without a single test going red.
//
// Scoped to the boot bundles on purpose, and read from hooks.py rather than
// hard-coded: an on-demand bundle (hierarchy-chart, interview) cannot race a
// list script, and extending a doctype whose folder this app does not own is a
// legitimate reason for one to write that key.
import { readFileSync as read } from "node:fs"

test("no file loaded at boot claims a doctype's listview_settings", () => {
	const here = fileURLToPath(new URL(".", import.meta.url))
	const hooks = read(`${here}../../hooks.py`, "utf8")
	const block = hooks.match(/app_include_js\s*=\s*\[([\s\S]*?)\]/)
	assert.ok(block, "app_include_js not found in hooks.py — this test has no subject")
	const entries = Array.from(block[1].matchAll(/"([^"]+\.js)"/g)).map((m) => m[1])
	assert.ok(entries.includes("fix_day.bundle.js"), "the Fix Day screen must still load at boot")
	for (const entry of entries) {
		assert.doesNotMatch(
			read(`${here}${entry}`, "utf8"),
			/frappe\.listview_settings\[[^\]]+\]\s*=/,
			`${entry}: the doctype's own list script owns that key and is loaded last`
		)
	}
})

// Owner, 17 Sep 2026, looking at Norazlin's 4 September on this screen: "uhm
// nope? no such 7pm stuff, the number att is different?" The Attendance
// section printed a status and some hours and NOTHING that identifies the row —
// no name, no shift — so the two lines could not be matched to the two rows the
// Attendance list shows, and the duplicate could not be told apart at all. The
// data was already there; only the line was missing it.
test("each attendance line says which row it is and on which shift", () => {
	const start = src.indexOf("function fd_row_line(")
	const body = src.slice(start, src.indexOf("\n}", start))
	assert.match(body, /row\.name/, "HR matches these lines against the Attendance list by name")
	assert.match(body, /row\.shift/, "the shift is how a 9AM-6PM row is told from a 7PM-3.30AM one")
})

// A rebuild the engine HELD — the never-worse guard rolled it back, or a
// protection refused the day — comes back with the day unchanged. Saying only
// "unchanged" leaves HR staring at a screen that did what they asked and shows
// nothing for it. The engine's own sentence is in the answer; print it.
test("a held rebuild tells HR why the day did not move", () => {
	const start = src.indexOf("show_change(answer) {")
	const body = src.slice(start, src.indexOf("\n\t}", start))
	assert.match(body, /answer\.rebuild/, "the engine's verdict per day is in the answer")
	assert.match(body, /held/, "a held day has a reason and HR needs to read it")
})

// Owner, 18 Sep 2026: the check-in page must read like the result, so the
// rebuild relabels the two taps that ARE the session. That rewrites what the
// device recorded, so HR sees it in the plan BEFORE pressing Apply — the same
// rule every other line of the plan follows.
test("the plan names a relabel before it happens", () => {
	const start = src.indexOf("plan_html(plan) {")
	const body = src.slice(start, src.indexOf("\n\t}", start))
	assert.match(body, /plan\.relabel/, "a rewritten punch label is not a silent change")
	assert.match(body, /Relabel/, "and it says so in words")
})

// Owner, 18 Sep 2026, having ticked both taps of ONE working day — an IN on the
// 3rd and its stranded OUT at 01:04 on the 4th — and been told "Tick taps of one
// person on one day": "yeah, now i cant do much."
//
// A shift that runs past midnight puts one session on two calendar dates. That
// is not a mistake to refuse, it is the commonest broken day in this system. The
// opener works out which day HR has to act on: the STRANDED tap's, because a
// tap with no shift is the one that needs moving, and it only lives on its own
// date. Two people, or dates further apart than a night, are still refused.
test("a session that crosses midnight can be opened", () => {
	const start = src.indexOf("hrms.fix_day.from_taps = function")
	const body = src.slice(start, src.indexOf("\n};", start))
	assert.doesNotMatch(
		body,
		/days\.size !== 1/,
		"a past-midnight session lands on two dates by nature; refusing it refuses the case"
	)
	assert.match(body, /employees\.size !== 1/, "two people is still two people")
	assert.match(body, /shift/, "the stranded tap — the one with no shift — names the day to open")
})

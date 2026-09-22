// The Fix Day screen: one button, one dialog, and still no control that types
// a result.
//
// Amended 22 Sep 2026. Seven of these tests were written against the six-action
// dialog (`run()`, `dedupe`, `claim_tap`, the relabel plan) that the 21 Sep
// one-button rewrite removed, and they had been red ever since — asserting
// buttons `hrms/tests/test_fix_day_screen.py` now pins as gone. Each is kept
// here as the INCIDENT it was written for, re-aimed at the screen that shipped:
// the owner's complaint outlives the button that answered it.
//
// Source-asserted, like the screen's Python-side test: this bundle runs inside
// Frappe's Desk and cannot be imported here.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("./fix_day.bundle.js", import.meta.url)), "utf8")

// Reported 17 Sep 2026: a day carrying two Attendance rows could not be reduced
// to one anywhere. The sixth action ("dedupe") closed that; the 21 Sep rewrite
// then folded it in — Save & rebuild cancels EVERY row of the day and rebuilds
// from the ticked pair, so a two-row day comes back as one without HR choosing
// a row. What must not come back is the screen choosing: it shows the rows it
// is about to replace, and names none of them to the server.
test("the screen shows the rows it will replace, and picks none of them", () => {
	const start = src.indexOf("render_summary() {")
	const body = src.slice(start, src.indexOf("\n\trender_primary(", start))
	assert.match(body, /state\.day\.attendance/, "HR sees today's rows before pressing Save")
	const args = src.slice(src.indexOf("args_for(date, reason) {"), src.indexOf("\n\tsave() {"))
	assert.doesNotMatch(args, /attendance:/, "which row may go is the server's call, not the screen's")
	assert.doesNotMatch(args, /linked_punches|auto_attendance|marked_by_hr/)
})

// Every correction used to have its own button and its own dialog, and the
// owner did one day through five of them (17 Sep 2026: "i want one step").
// There is one write now, and it must stay one: a second call site for
// `save_day` is a second way for a day to change.
test("there is exactly one way to write a day", () => {
	const writes = src.match(/FD_API \+ "(\w+)"/g) || []
	const saves = writes.filter((call) => call.includes("save_day"))
	assert.equal(saves.length, 1, "save_day has one call site — save_one()")
	assert.match(
		src,
		/save_one\(date, reason, results\) \{\s*return fd_call\(FD_API \+ "save_day"/,
		"and it is reached through save(), which checks the reason and the plan of every day first"
	)
})

// The owner rule the whole feature exists to keep: HR states the EVIDENCE (which
// punches are real, on which shift, and why) and the engine states the result.
// Anything in this payload that looks like an outcome is a way round it.
test("Save sends evidence, and no result", () => {
	const start = src.indexOf("args_for(date, reason) {")
	assert.ok(start > 0, "the payload is built in one place")
	const body = src.slice(start, src.indexOf("\n\tsave() {", start))
	assert.match(body, /pairs:/, "the ticked IN and OUT of each session")
	assert.match(body, /delete:/, "the punches that are not real")
	assert.match(body, /reason,/, "recorded on every punch and in the fix log")
	assert.match(body, /seen_modified:/, "the day HR actually looked at (G11)")
	for (const word of ["hours", "status", "overtime", "ot_"]) {
		assert.doesNotMatch(body, new RegExp(`${word}\\s*:`, "i"), `${word} is computed, never sent`)
	}
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
// section printed a status and some hours and NOTHING that identifies the row,
// so the two lines could not be matched to the two rows the Attendance list
// shows. The record id went back out on 21 Sep ("no record ids") — the SHIFT
// and the clocks are what tell a 9AM-6PM row from a 7PM-3.30AM one, and they
// are what must never go.
test("each attendance line says which shift it is and when", () => {
	const start = src.indexOf("function fd_row_line(")
	const body = src.slice(start, src.indexOf("\n}", start))
	assert.match(body, /row\.shift/, "the shift tells the two rows of one day apart")
	assert.match(body, /row\.in_time/, "and the clocks say which session it is")
	assert.match(body, /row\.out_time/)
})

// A rebuild the engine HELD — the never-worse guard rolled it back, or a
// protection refused the day — comes back with the day unchanged. Saying only
// "rebuilt" leaves HR staring at a screen that did what they asked and shows
// nothing for it. The engine's own sentence is in the answer; print it.
test("a held rebuild tells HR why the day did not move", () => {
	const start = src.indexOf("result_html(date, answer) {")
	assert.ok(start > 0, "the per-day answer is painted in one place")
	const body = src.slice(start, src.indexOf("\n\t// Undo", start))
	assert.match(body, /answer\.rebuild/, "the engine's verdict per day is in the answer")
	assert.match(body, /"held"/, "a held day has a reason and HR needs to read it")
	assert.match(body, /verdict\.detail/, "and the reason itself, not just the fact")
})

// Owner, 18 Sep 2026: a rebuild rewrites what the device recorded, so HR sees
// every change in words BEFORE pressing Save — the row that will exist, and how
// many punches go. Nothing about this day may change that was not on screen.
test("the summary names every change before Save can be pressed", () => {
	const start = src.indexOf("render_summary() {")
	const body = src.slice(start, src.indexOf("\n\trender_primary(", start))
	assert.match(body, /this\.after_line\(plan/, "the row the ticks will make")
	assert.match(body, /this\.to_delete\(state\)\.length/, "and how many punches will be deleted")
	assert.match(body, /will be deleted/, "said in words, with the Undo")
	assert.match(
		body,
		/if \(plan\.error\) this\.dialog\.disable_primary_action\(\)/,
		"a day the screen cannot state is a day it will not save"
	)
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

// A mirrored tap had no tick box at all, so the punch HR must now take over was
// the one punch they could not select (owner, 18 Sep 2026: "i cant do much").
// `claim_tap` was that answer and the 21 Sep rewrite retired it; the rule it
// left behind is stronger — EVERY punch the screen lists can be ticked. The one
// exception is a punch an approved request put there (G7), which is locked
// because removing it would contradict a decision already taken.
test("every punch listed can be ticked, except one an approved request owns", () => {
	const start = src.indexOf("tap_html(row) {")
	const body = src.slice(start, src.indexOf("\n\ttaps_html(", start))
	const box = body.match(/<input type="checkbox"[^>]*>/)
	assert.ok(box, "every row carries a tick box")
	assert.doesNotMatch(box[0], /mirrored|state|hidden/, "no punch is unselectable by where it came from")
	assert.match(body, /const disabled = row\.locked \? " disabled" : ""/, "only a locked punch is")
	assert.match(src, /const locked = Boolean\(tap\.linked_request\)/, "and locked means an approved request")
})

// --- the unreadable day (22 Sep 2026) ------------------------------------------
//
// Adam Daniel's 18 August: 4 punches, the dialog opened with 3 IN and 1 OUT
// ticked, printed its own refusal and Save & rebuild did nothing. The pre-tick
// was the cause: `day_plan` suggests a pair only when it can READ the day, so on
// the broken days HR actually opens this for, `suggested` is empty and the old
// fallback ticked EVERY counted punch. Four ticks are never 1 IN + 1 OUT, so the
// dialog disabled its own primary action and the day was unfixable.
//
// A refusal is information, not an absence.

test("an unreadable day pre-ticks nothing and shows the engine's reason", () => {
	const start = src.indexOf("fresh_state(day) {")
	assert.ok(start > 0, "fresh_state exists")
	const body = src.slice(start, src.indexOf("\n\tdefault_shift(", start))
	assert.match(
		body,
		/day\.suggestion_refusal/,
		"the planner's refusal must be read, not inferred from an empty suggestion"
	)
	assert.match(
		body,
		/unreadable\s*\?\s*false\s*:/,
		"on an unreadable day no punch is pre-ticked — HR ticks the real pair"
	)
})

test("the engine's refusal reaches the summary, so HR reads why", () => {
	assert.match(
		src,
		/render_summary\(\)\s*\{[\s\S]*?suggestion_refusal/,
		"the sentence is shown above the ticks"
	)
})

// A punch of this shift-day landing the NEXT calendar morning read as "07:38"
// directly under a 07:39 of the day before — two punches 24 h apart looked like
// a twin. The clock cell must carry the date when it is not the day being fixed.
test("a punch landing the next morning is shown with its date", () => {
	const start = src.indexOf("tap_html(row) {")
	assert.ok(start > 0, "tap_html exists")
	const body = src.slice(start, src.indexOf("\n\ttaps_html(", start))
	assert.match(body, /row\.day_label/, "the clock cell shows which day the punch is on")
})

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

// The class, not the instance. This bundle loads at boot; a doctype's list
// script loads when the list opens, and assigns frappe.listview_settings for
// that doctype outright. Whatever a bundle wrote there is gone. That cost HR
// the "Fix day" button on Employee Checkin for a week without a single test
// going red, so no file shipped at boot may write that key again.
import { readdirSync } from "node:fs"

test("no boot bundle claims a doctype's listview_settings", () => {
	const dir = fileURLToPath(new URL(".", import.meta.url))
	for (const file of readdirSync(dir).filter((f) => f.endsWith(".js"))) {
		const text = readFileSync(`${dir}${file}`, "utf8")
		assert.doesNotMatch(
			text,
			/frappe\.listview_settings\[[^\]]+\]\s*=/,
			`${file}: the doctype's own list script owns that key and is loaded last`
		)
	}
})

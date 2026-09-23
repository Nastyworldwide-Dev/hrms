// One status map: every status word on screen takes its colour from
// utils/requestStatus.js (via GStatusChip), never from a local table.
//
// FormattedField kept its own three-entry colorMap (Approved/Rejected/Open)
// and drew a frappe-ui Badge, so the same "Approved" rendered one way in a
// review sheet's fields and another in every list beside it.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("FormattedField draws a Select value with GStatusChip, not its own colorMap", () => {
	const src = read("../FormattedField.vue")
	assert.doesNotMatch(src, /colorMap/, "no local status -> colour table")
	assert.doesNotMatch(src, /<Badge\b/, "no frappe-ui Badge")
	assert.match(src, /<GStatusChip[\s\S]*?:status="props\.value"/)
})

test("no second status -> colour guesser survives", () => {
	// guessStatusColor fetched a doctype's state colours and keyword-guessed
	// the rest, for a `statusColor` FormView never rendered: a second map
	// that cost a request per status change and fed nothing.
	assert.doesNotMatch(read("../../composables/index.js"), /guessStatusColor/)
	assert.doesNotMatch(read("../FormView.vue"), /guessStatusColor|statusColor/)
})

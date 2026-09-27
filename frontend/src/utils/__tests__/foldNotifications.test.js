// alpha.13 slice 3 (owner ruling R6): within a day, the same person asking for
// the same kind of thing is ONE row with a count — "W0 employee asked for time
// off · 3" — the newest leading. One-of-a-kind rows stay as they are.
import { test } from "node:test"
import assert from "node:assert/strict"
import { foldNotifications } from "../foldNotifications.js"

const n = (name, from, kind, read = 0) => ({ name, from_user: from, reference_document_type: kind, read })

test("same person + same kind fold, newest first; others stay single", () => {
	const items = [
		n("5", "a", "Leave Application"),
		n("4", "a", "Leave Application"),
		n("3", "b", "Leave Application"),
		n("2", "a", "Expense Claim"),
		n("1", "a", "Leave Application"),
	]
	const folded = foldNotifications(items)
	assert.deepEqual(
		folded.map((f) => [f.lead.name, f.members.map((m) => m.name)]),
		[
			["5", ["5", "4", "1"]],
			["3", ["3"]],
			["2", ["2"]],
		]
	)
})

test("a fold is unread while any member is unread", () => {
	const [fold] = foldNotifications([n("2", "a", "OT Request", 1), n("1", "a", "OT Request", 0)])
	assert.equal(fold.unread, 1)
	const [done] = foldNotifications([n("2", "a", "OT Request", 1), n("1", "a", "OT Request", 1)])
	assert.equal(done.unread, 0)
})

test("the order of the day is kept: a fold sits where its newest member was", () => {
	const folded = foldNotifications([n("3", "b", "Shift Request"), n("2", "a", "Leave Application"), n("1", "b", "Shift Request")])
	assert.deepEqual(folded.map((f) => f.lead.name), ["3", "2"])
})

import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
const view = readFileSync(fileURLToPath(new URL("../../views/Notifications.vue", import.meta.url)), "utf8")

test("the screen draws folds, opens a fold inline, and marks a fold read in one call", () => {
	assert.match(view, /foldNotifications\(/)
	assert.match(view, /v-for="fold in group\.folds"/)
	assert.match(view, /hrms\.api\.mark_notifications_as_read/)
	assert.match(view, /:aria-expanded="fold\.members\.length > 1 \? String\(isOpen\(fold\)\)/)
})

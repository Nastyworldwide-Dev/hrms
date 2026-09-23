// Help reads "what's still open" first, 5 at a time; everything finished is
// one row away (owner: "drowned with information", 23 Sep 2026; NN/g
// progressive disclosure). A row is two short lines: title, then the day and
// "Waiting on you" when it is — never the id, the type or "by <you>".
import { test } from "node:test"
import assert from "node:assert/strict"

import { helpRowMeta, splitHelp } from "../helpdesk.js"

const T = (status, n) => ({ name: String(n), status, subject: `t${n}`, modified: "2026-09-21 13:08:00" })

test("open and waiting-on-you tickets come first; resolved and closed are a separate pile", () => {
	const { open, done } = splitHelp([T("Closed", 1), T("Open", 2), T("Replied", 3), T("Resolved", 4), T("Paused", 5)])
	assert.deepEqual(open.map((r) => r.name), ["3", "2", "5"], "waiting on you sorts to the top")
	assert.deepEqual(done.map((r) => r.name), ["1", "4"])
})

test("HR issue statuses split the same way", () => {
	const { open, done } = splitHelp([
		{ name: "a", status: "Open" },
		{ name: "b", status: "In Progress" },
		{ name: "c", status: "Completed" },
		{ name: "d", status: "Rejected" },
	])
	assert.deepEqual(open.map((r) => r.name), ["a", "b"])
	assert.deepEqual(done.map((r) => r.name), ["c", "d"])
})

test("the second line is the day, plus 'Waiting on you' — never the id or who raised it", () => {
	const day = () => "21 Sep"
	assert.equal(helpRowMeta({ name: "0871", status: "Replied", raised_by_name: "Rasul" }, { day }), "21 Sep · Waiting on you")
	assert.equal(helpRowMeta({ name: "HR-ISS-26-09-00002", status: "Open", details: "Test" }, { day }), "21 Sep")
})

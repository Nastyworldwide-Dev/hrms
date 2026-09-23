// Approvals say whose turn it is (2.0 slice 4.1, UX_PLAN §3.5).
//
// (History) The screen was titled "Remote Approvals" and its two tabs are "Pending" and
// "History". All three are the system's vocabulary rather than the approver's.
// "Pending" does not say pending on WHOM — the approver's own list and the
// employee's both contain pending things, and only one of them is this
// approver's problem. The plan's words are "Waiting on you" and "Decided by
// you", which answer that.
//
// WHAT THIS SLICE IS NOT. §3.5 also asks for a UNIFIED queue — every request
// type in one list, over a new `approval.list_pending_for_user` endpoint that
// does not exist. The plan marks it **N** (new backend), and §7 puts new
// backend out of 2.0's scope. So this is the wording and the counts, which is
// what §6's row asks for; the queue is its own piece of work with its own
// endpoint.
//
// "Remote" stays in the title for the same reason it stays in the NeedsYou
// row: this screen shows remote check-in approvals ONLY, and an approver who
// reads a bare "Approvals" would take it for all of them and stop looking.
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

// 23 Sep 2026: the Remote approvals page folded into the one Approvals page
// (AUDIT-PLAN, Approvals row), so the rules below now hold there.
test("the page says whose turn it is", () => {
	const view = code(read("views/Approvals.vue"))
	assert.match(view, /__\("Nothing is waiting on you\."\)/, "the empty state names the reader")
	assert.match(view, /__\("Check-ins you've already answered"\)/, "and what they already decided")
	assert.doesNotMatch(view, /__\("Pending"\)|__\("History"\)/, "not the system's words")
})

test("a check-in row says what it is, not 'remote'", () => {
	// The row's kind comes from the server, in the person's words.
	const server = read("../../hrms/api/approvals_list.py")
	assert.match(server, /"kind": "Check-in outside the area"/)
})

test("the approver is told how many are waiting", () => {
	// An approver opening the screen wants to know whether this is a
	// two-minute job before they start reading rows. A number in a SENTENCE,
	// not a `.length` in a v-if.
	const view = code(read("views/Approvals.vue"))
	assert.match(view, /__\("\{0\} waiting"/, "the count is stated, not left to be counted by eye")
})

test("the helpdesk pills name the two places, not the two apps", () => {
	// "HR Issues" and "IT Helpdesk" are already the employee's words — this
	// pins them, because the consolidation that produced them (one page, two
	// pills) is the kind of thing a later edit re-splits.
	const hub = code(read("views/helpdesk/HelpdeskHub.vue"))
	// alpha.5 Help redesign: the pills are "HR" / "IT" (segmented control,
	// Apple HIG: short segment labels); the page title already says Help.
	assert.match(hub, /__\("HR"\)/, "the HR side")
	assert.match(hub, /__\("IT"\)/, "and the IT side, when the app is installed")
	assert.doesNotMatch(hub, /__\("Employee Issue"\)/, "that is the doctype")
})

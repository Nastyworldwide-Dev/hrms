// Approvals say whose turn it is (2.0 slice 4.1, UX_PLAN §3.5).
//
// The screen is titled "Remote Approvals" and its two tabs are "Pending" and
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

test("the tabs say whose turn it is", () => {
	// "Pending" does not say pending on whom. Both lists on this screen contain
	// pending things; only one of them is waiting on the person reading it.
	const view = code(read("views/RemoteApprovals.vue"))
	// The constant is `{ key, label }` objects now, so it spans lines — match
	// to the closing bracket of the whole array, not the first one.
	const tabs = view.match(/const TAB_BUTTONS = \[([\s\S]*?)\n\]/)
	assert.ok(tabs, "the tabs are a named constant")
	assert.match(tabs[1], /Waiting on you/, "the first list is the approver's queue")
	assert.match(tabs[1], /Decided by you/, "the second is what they have already answered")
	// The KEYS keep those words — they are compared in the template and carried
	// in a deep link. What must not say them is the LABEL.
	const labels = [...tabs[1].matchAll(/label: __\("([^"]*)"\)/g)].map((m) => m[1])
	assert.deepEqual(labels, ["Waiting on you", "Decided by you"])
})

test("the tab labels are translated where they render", () => {
	// A tab constant is a list of KEYS as well as labels — the template
	// compares `activeTab === "..."` against them — so translating in place
	// would break the comparison. The labels must go through `__()` at the
	// render site instead, which is the pattern GSegmented already expects.
	const view = code(read("views/RemoteApprovals.vue"))
	assert.match(view, /label: __\(/, "each label goes through the translator where it is defined")
	assert.match(view, /key: "Pending"/, "and the key it is paired with is the untranslated one")
})

test('"remote" survives, because the list is remote-only', () => {
	// The same rule the NeedsYou row carries: this screen shows remote
	// check-in approvals and nothing else, so a bare "Approvals" would invite
	// an approver to believe they had seen everything.
	// The TITLE, not the word anywhere in the file — "Remote" appears eight
	// times here, so a bare match passed against a mutant that renamed the
	// heading.
	const view = code(read("views/RemoteApprovals.vue"))
	const heading = view.slice(view.indexOf("<h2"), view.indexOf("</h2>"))
	assert.match(heading, /Remote/, "the scope is part of the name")
})

test("the approver is told how many are waiting", () => {
	// §3.5 asks for a count. An approver opening the screen wants to know
	// whether this is a two-minute job before they start reading rows.
	const view = code(read("views/RemoteApprovals.vue"))
	// A `.length` in a `v-if` is a RENDER decision, not a count shown to
	// anybody — the first version of this matched one and passed against a
	// screen that states no count at all. What is asserted is a number in a
	// SENTENCE.
	assert.match(
		view,
		/__\("\{0\} waiting[^"]*"|__\("\{0\} to decide/,
		"the count is stated, not left to be counted by eye"
	)
})

test("the helpdesk pills name the two places, not the two apps", () => {
	// "HR Issues" and "IT Helpdesk" are already the employee's words — this
	// pins them, because the consolidation that produced them (one page, two
	// pills) is the kind of thing a later edit re-splits.
	const hub = code(read("views/helpdesk/HelpdeskHub.vue"))
	assert.match(hub, /__\("HR Issues"\)/, "the HR side")
	assert.match(hub, /__\("IT Helpdesk"\)/, "and the IT side, when the app is installed")
	assert.doesNotMatch(hub, /__\("Employee Issue"\)/, "that is the doctype")
})

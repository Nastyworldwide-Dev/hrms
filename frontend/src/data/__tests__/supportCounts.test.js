// How many things YOU have open, on each Helpdesk pill (revamp §7, slice D3).
//
// The hub has had two pills since 15 September and neither said whether there
// was anything behind it, so an employee with an unanswered HR issue had to
// open the pill to find out — every time, including the times there was
// nothing.
//
// THE COUNT COMES FROM THE SAME ROWS THE LIST SHOWS. An independent count
// query is a second answer that can disagree with the list it labels, and a
// pill reading "2" above a list of three is worse than a pill with no number.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

//: The module cannot be imported directly — it uses Vite's `@/` alias, which
//: node does not resolve — so the pure parts are evaluated in isolation and
//: the rest is read. Whatever depends on frappe-ui's resources is stubbed:
//: what is being tested is the CLASSIFICATION, not the fetch.
const HERE = fileURLToPath(new URL(".", import.meta.url))
const source = readFileSync(join(HERE, "../supportCounts.js"), "utf8")

const stubbed = source
	.replace(/^import[\s\S]*?from\s+"[^"]+"\s*$/gm, "")
	.replace(/createListResource\(/g, "stubResource(")
	.replace(/\bmyTickets\b/g, "stubTickets")
	.replace(/personalCacheKey\([^)]*\)/g, "null")
	.replace(/export /g, "")

const context = {}
// The stubs are PARAMETERS, not globals: a `new Function` body sees the
// function's own arguments, never the closure it was built in.
// eslint-disable-next-line no-new-func
new Function(
	"context",
	"stubResource",
	"stubTickets",
	`${stubbed}; Object.assign(context, { OPEN_ISSUE_STATUSES, OPEN_TICKET_STATUSES, myIssuesForCount, openIssueCount, openTicketCount })`
)(context, (options) => ({ ...options, data: null }), { data: null })

const {
	OPEN_ISSUE_STATUSES,
	OPEN_TICKET_STATUSES,
	myIssuesForCount,
	openIssueCount,
	openTicketCount,
} = context

test("open is an allow-list, not everything-except-closed", () => {
	// A new status added to either doctype must be classified DELIBERATELY. A
	// "not closed" test silently counts whatever appears next, which is how a
	// pill starts including archived rows nobody can act on.
	assert.ok(OPEN_ISSUE_STATUSES.length > 0)
	for (const done of ["Closed", "Resolved", "Cancelled"]) {
		assert.ok(!OPEN_ISSUE_STATUSES.includes(done), `${done} is not open`)
		assert.ok(!OPEN_TICKET_STATUSES.includes(done), `${done} is not open`)
	}
})

test("a ticket waiting on the EMPLOYEE counts", () => {
	// HD Ticket's "Replied" means the agent answered and it is now waiting on
	// the person reading the pill. That is the state people forget they are
	// holding, so it is the most important one to surface.
	assert.ok(OPEN_TICKET_STATUSES.includes("Replied"))
})

test("a missing list counts as zero, never as an error", () => {
	// A pill that cannot count is a pill without a number. It is not a page
	// that fails to open.
	const before = myIssuesForCount.data
	try {
		myIssuesForCount.data = undefined
		assert.equal(openIssueCount(), 0)
		myIssuesForCount.data = null
		assert.equal(openIssueCount(), 0)
		// Not an array — a resource that errored can leave an object here.
		myIssuesForCount.data = { message: "nope" }
		assert.equal(openIssueCount(), 0)
	} finally {
		myIssuesForCount.data = before
	}
})

test("only open rows are counted", () => {
	const before = myIssuesForCount.data
	try {
		myIssuesForCount.data = [
			{ status: "Open" },
			{ status: "Closed" },
			{ status: "In Progress" },
			{ status: "Resolved" },
			{ status: undefined },
		]
		assert.equal(openIssueCount(), 2, "Open and In Progress; nothing else")
	} finally {
		myIssuesForCount.data = before
	}
})

test("the issue count does not fetch on import", () => {
	// It is fetched when the hub mounts. A module-level fetch would run on
	// every screen that imports the hub's siblings, including before sign-in.
	assert.equal(myIssuesForCount.auto, false)
})

test("the ticket count reads the list the pill itself renders", () => {
	// Literally the same array — so the number and the rows cannot disagree.
	assert.equal(typeof openTicketCount, "function")
	assert.match(source, /import \{ myTickets \} from "@\/data\/helpdesk"/)
	assert.match(source, /countOpen\(myTickets\.data/)
})

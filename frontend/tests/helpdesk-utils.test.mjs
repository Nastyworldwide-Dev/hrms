// Pure helpers behind the native Helpdesk screens. The chip buckets and the
// thread merge are the two places a wrong status word or a mis-attributed
// message would silently mislead an employee, so they are pinned here.
// Run: cd frontend && node --experimental-test-module-mocks --test tests/helpdesk-utils.test.mjs
import { test } from "node:test"
import assert from "node:assert/strict"

import { filterTickets, statusLabel, threadFromTicket } from "../src/utils/helpdesk.js"

const T = (name, status) => ({ name, status })

test("chips bucket by status word; unknown statuses only ever show under All", () => {
	const list = [T("a", "Open"), T("b", "Replied"), T("c", "Resolved"), T("d", "Closed"), T("e", "Paused"), T("f", "Weird")]
	assert.deepEqual(filterTickets(list, "all").map((t) => t.name), ["a", "b", "c", "d", "e", "f"])
	assert.deepEqual(filterTickets(list, "open").map((t) => t.name), ["a", "e"])
	assert.deepEqual(filterTickets(list, "replied").map((t) => t.name), ["b"])
	assert.deepEqual(filterTickets(list, "resolved").map((t) => t.name), ["c", "d"])
	assert.deepEqual(filterTickets(undefined, "open"), [])
})

test("Replied reads as Awaiting you; other statuses pass through", () => {
	assert.equal(statusLabel("Replied"), "Awaiting you")
	assert.equal(statusLabel("Open"), "Open")
	assert.equal(statusLabel(""), "")
})

test("thread merges the description, communications and comments in time order", () => {
	const ticket = {
		description: "<p>It broke</p>",
		raised_by: "amy@x.com",
		raised_by_name: "Amy E.",
		opening_date: "2026-09-01",
		creation: "2026-09-01 08:00:00",
		communications: [
			{ name: "c2", content: "Fixed it", creation: "2026-09-01 10:00:00", sender: "agent@x.com", sent_or_received: "Sent", user: { name: "agent@x.com", full_name: "Nabil Z." } },
			{ name: "c1", content: "Still broken", creation: "2026-09-01 09:00:00", sender: "amy@x.com", sent_or_received: "Received", user: { name: "amy@x.com", full_name: "Amy E." } },
		],
		comments: [{ name: "k1", content: "internal note", creation: "2026-09-01 09:30:00", commented_by: "agent@x.com", user: { full_name: "Nabil Z." } }],
	}
	const thread = threadFromTicket(ticket, "amy@x.com")
	assert.deepEqual(
		thread.map((m) => [m.kind, m.who]),
		[
			["me", "Amy E."],
			["me", "Amy E."],
			["agent", "Nabil Z."],
			["agent", "Nabil Z."],
		]
	)
	assert.equal(thread[0].html, "<p>It broke</p>")
})

test("a viewer who is not the raiser sees the raiser's messages as theirs, not 'me'", () => {
	const ticket = {
		description: "x",
		raised_by: "amy@x.com",
		raised_by_name: "Amy E.",
		creation: "2026-09-01 08:00:00",
		communications: [],
		comments: [],
	}
	const thread = threadFromTicket(ticket, "hr@x.com")
	assert.equal(thread[0].kind, "agent")
	assert.equal(thread[0].who, "Amy E.")
})

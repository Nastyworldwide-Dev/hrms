// "Waiting" that does not say on whom (mockup 4 gap #1, 23 September 2026).
//
// The employee's own request list showed a type, a date and a chip reading
// WAITING. Mockup 4's row reads "Annual leave · with Hafiz since Monday", and
// the difference is not decoration: somebody looking at their own list is
// almost always working out who to chase and how long it has been. Without
// those facts they ask HR, and HR asks us.
//
// It is the same defect 2.0 fixed on the APPROVALS screen — where "Pending"
// became "Waiting on you" — and never fixed on the side of the app where the
// person is doing the waiting.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync, readdirSync } from "node:fs"
import { join } from "node:path"
import { fileURLToPath } from "node:url"

import { waitingWith } from "../requestWaiting.js"

//: The translator's real shape: a template and positional arguments.
const t = (s, args = []) => s.replace(/\{(\d+)\}/g, (_, i) => args[i])
const since = () => "2 days ago"

test("a waiting request names who has it and since when", () => {
	assert.equal(
		waitingWith(
			{ approver_name: "Hafiz", posting_date: "2026-09-21" },
			{ pending: true, since, t }
		),
		"with Hafiz · 2 days ago"
	)
})

test("a DECIDED request says nothing", () => {
	// It is not waiting on anybody. A line reading "with Hafiz" under an
	// Approved chip invites the reader to chase somebody who has already done
	// their part.
	assert.equal(
		waitingWith(
			{ approver_name: "Hafiz", posting_date: "2026-09-21" },
			{ pending: false, since, t }
		),
		""
	)
})

test("no approver still says how long", () => {
	// Real case: attendance and OT requests route by reporting line and carry
	// no approver field at all. Half the sentence is still worth having.
	assert.equal(
		waitingWith({ posting_date: "2026-09-21" }, { pending: true, since, t }),
		"waiting 2 days ago"
	)
})

test("no date still says who", () => {
	assert.equal(waitingWith({ approver_name: "Hafiz" }, { pending: true, since, t }), "with Hafiz")
})

test("nothing true to say renders nothing", () => {
	// An empty string is the signal to render no line at all. "with —" is
	// worse than silence: it looks like data that failed to load.
	assert.equal(waitingWith({}, { pending: true, since, t }), "")
	assert.equal(waitingWith(null, { pending: true, since, t }), "")
	assert.equal(waitingWith(undefined, { pending: true, since, t }), "")
})

test("the clock starts when the employee filed it", () => {
	// `posting_date` is the date they remember and the one the approver is
	// late against. `creation` is the fallback for payloads without it.
	const seen = []
	waitingWith(
		{ approver_name: "Hafiz", posting_date: "2026-09-21", creation: "2026-01-01" },
		{ pending: true, since: (d) => (seen.push(d), "x"), t }
	)
	assert.deepEqual(seen, ["2026-09-21"], "posting_date wins")

	seen.length = 0
	waitingWith(
		{ approver_name: "Hafiz", creation: "2026-01-01" },
		{ pending: true, since: (d) => (seen.push(d), "x"), t }
	)
	assert.deepEqual(seen, ["2026-01-01"], "creation is the fallback")
})

test("every row component uses the one helper", () => {
	// Six request-row components. A sentence written six times is a sentence
	// that drifts five times — which is how "Pending", "Open" and "Draft" came
	// to mean the same thing on three screens.
	const components = join(fileURLToPath(new URL("../..", import.meta.url)), "components")
	const rows = readdirSync(components).filter((f) => /RequestItem\.vue$|ClaimItem\.vue$/.test(f))
	assert.ok(rows.length >= 5, `expected the request rows, found ${rows.length}`)
	for (const file of rows) {
		const source = readFileSync(join(components, file), "utf8")
		assert.match(source, /waitingWith/, `${file} builds the line itself`)
		assert.match(source, /v-if="waiting"/, `${file} renders it`)
		assert.match(source, /props\.isTeamRequest\s*\n?\s*\?\s*""/, `${file} hides it on a team row`)
		// AND the pending flag comes from the real verdict, unmodified. A
		// mutation that hardcoded it survived the first version of this test —
		// which would have put "with Hafiz" under an Approved chip, inviting
		// the reader to chase somebody who has already decided.
		assert.match(
			source,
			/pending: (?:verdict\.value\.pending|requestStatus\("[^"]+", props\.doc\)\.pending),/,
			`${file} reads pending from requestStatus and nothing else`
		)
	}
})

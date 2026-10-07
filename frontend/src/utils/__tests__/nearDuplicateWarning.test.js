// The near-duplicate expense warning reaches the employee in Nadi (alpha.38, owner 6 Oct 2026).
//
// Saving a claim that looks like another (same type, same day, another amount) msgprints an
// orange warning on the server. Nadi never showed it: frappe-ui drops `_server_messages` on a
// successful request, so the employee read "Your expense claim was created." and nothing else.
// After a create, the form now asks hrms.api.near_duplicate_expenses for the claim and toasts
// each sentence once, as a warning. An empty answer says nothing.
// Run: cd frontend && node --test src/utils/__tests__/nearDuplicateWarning.test.js
import { test } from "node:test"
import assert from "node:assert/strict"

import { warnOfNearDuplicates } from "../nearDuplicateWarning.js"

const __ = (text) => text
const SENTENCE =
	"You already claimed a Travel on 01-10-2026 in HR-EXP-0001. Check it is not the same expense."

function harness(answer) {
	const asked = []
	const toasts = []
	return {
		asked,
		toasts,
		run: () =>
			warnOfNearDuplicates("HR-EXP-0002", {
				ask: async (name) => {
					asked.push(name)
					if (answer instanceof Error) throw answer
					return answer
				},
				notify: (t) => toasts.push(t),
				__,
			}),
	}
}

test("the created claim is asked about, by its own name, once", async () => {
	const h = harness([SENTENCE])
	await h.run()
	assert.deepEqual(h.asked, ["HR-EXP-0002"])
})

test("each sentence is toasted as a warning, with the server's words", async () => {
	const other =
		"You already claimed a Meals on 01-10-2026 in HR-EXP-0003. Check it is not the same expense."
	const h = harness([SENTENCE, other])
	const shown = await h.run()
	assert.equal(shown, 2)
	assert.deepEqual(
		h.toasts.map((t) => [t.variant, t.text]),
		[
			["warning", SENTENCE],
			["warning", other],
		]
	)
	for (const t of h.toasts) assert.ok(t.title, "a warning says what it is about")
})

test("nothing near it: no toast at all", async () => {
	for (const empty of [[], null, undefined]) {
		const h = harness(empty)
		assert.equal(await h.run(), 0)
		assert.deepEqual(h.toasts, [])
	}
})

test("the sentence goes to the toast as written; gToast is the one place that escapes it", async () => {
	// review of 006dc82a3: this util escaped AND gToast escaped, so "Travel & Meals" showed as
	// "Travel &amp; Meals". Safety for the v-html toast lives in glass/toast.js.
	const sentence = "You already claimed a Travel & Meals <b> on 01-10-2026 in HR-EXP-0001."
	const h = harness([sentence])
	await h.run()
	assert.equal(h.toasts[0].text, sentence)
})

test("a failed lookup never undoes the create: it is logged and nothing is toasted", async () => {
	const log = console.warn
	const logged = []
	console.warn = (...args) => logged.push(args.join(" "))
	try {
		const h = harness(new Error("boom"))
		assert.equal(await h.run(), 0)
		assert.deepEqual(h.toasts, [])
		assert.match(
			logged.join("\n"),
			/HR-EXP-0002/,
			"the failure is on the console, with the claim named"
		)
	} finally {
		console.warn = log
	}
})

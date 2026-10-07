// A server refusal reaches a person as plain words. firstMessage is the ONE reader, shared with
// the forms; it returns text and nothing else, so what it hands over is only ever as safe as the
// sink that renders it. That sink is components/glass/toast.js (gToast), which escapes; this file
// never makes markup safe, and a source check below keeps it from growing a second sink.
//
// Executes the real module: it imports nothing, so no harness is needed.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

import { firstMessage, saveFailedSentence } from "../refusalText.js"
import { withOnline } from "./_online.js"

const PERMISSION_ERROR = {
	exc_type: "PermissionError",
	messages: ["Insufficient Permission for Account"],
}
const NO_NETWORK = new TypeError("Failed to fetch")

// One row per shape a refusal arrives in: [what it is, the error, the words]. A fix for a new shape
// adds a row here, not another test.
const SHAPES = [
	// markup: real tags go, their words stay
	["an inline tag", { messages: ["Ask <b>HR</b> now"] }, "Ask HR now"],
	[
		"a Desk link",
		{ messages: ['Already applied: <a href="/app/leave-application/HR-LAP-1">HR-LAP-1</a>'] },
		"Already applied: HR-LAP-1",
	],
	["a tag in capitals", { messages: ["Ask <B>HR</B> now"] }, "Ask HR now"],
	["a lone tag and nothing else", { messages: ["<b>"] }, ""],
	[
		"a script block (text kept, tags gone; the toast escapes)",
		{ messages: ["<script>alert(1)</script>Refused"] },
		"alert(1)Refused",
	],
	// comparisons are not tags (reviews of 96ac1b8e1 and f35e2b982)
	["a less-than comparison", { messages: ["Hours must be < 8"] }, "Hours must be < 8"],
	["a greater-than comparison", { messages: ["Hours must be > 0"] }, "Hours must be > 0"],
	["a less-or-equal comparison", { messages: ["x <= 5 and y >= 2"] }, "x <= 5 and y >= 2"],
	["an arrow", { messages: ["Go -> next"] }, "Go -> next"],
	// entities are neither decoded nor encoded here
	["entities", { messages: ["Hours &lt; 8 &amp; more"] }, "Hours &lt; 8 &amp; more"],
	// line breaks keep a space between the parts (review of 3169ca158)
	[
		"a <br>",
		{ messages: ["Leave overlaps<br>Pick other days"] },
		"Leave overlaps Pick other days",
	],
	["a <br/>", { messages: ["Line<br/>two"] }, "Line two"],
	["a <BR> in capitals", { messages: ["A<BR>B"] }, "A B"],
	["paragraphs", { messages: ["<p>First.</p><p>Second.</p>"] }, "First. Second."],
	["list items", { messages: ["<ul><li>One</li><li>Two</li></ul>"] }, "One Two"],
	["divs", { messages: ["<div>one</div><div>two</div>"] }, "one two"],
	["a tab and a newline", { messages: ["Tab\tand\nnewline"] }, "Tab and newline"],
	// unclosed or half-open markup (review of 96ac1b8e1)
	["an unclosed comment", { messages: ["x <!-- unclosed"] }, "x"],
	["a closed comment", { messages: ["<!-- note -->Refused"] }, "Refused"],
	["an unfinished tag", { messages: ["Refused <b"] }, "Refused <b"],
	["an unfinished script tag", { messages: ["Refused <script"] }, "Refused <script"],
	// the reason itself
	["the server's own sentence", PERMISSION_ERROR, "Insufficient Permission for Account"],
	["a first message among several", { messages: ["First", "Second"] }, "First"],
	["a message with no list", { message: "Network down" }, "Network down"],
	// nothing to say
	["no error at all", undefined, "Request failed"],
	["no error, the caller's words", undefined, "Request failed", "Try again."],
	["an empty message list", { messages: [] }, "Request failed"],
	["an empty first message falls to the next field", { messages: [""], message: "m" }, "m"],
]

for (const [what, error, words, fallback] of SHAPES) {
	test(`firstMessage reads ${what}`, () => {
		// a caller's own wording stands in only when there is no message at all
		assert.equal(firstMessage(error, fallback), fallback ?? words)
	})
}

test("a caller's own wording never replaces a message the server did send", () => {
	assert.equal(firstMessage({ messages: ["Refused"] }, "Try again."), "Refused")
})

test("a network failure reads as plain words everywhere, never 'Failed to fetch'", () => {
	withOnline(false, () => assert.equal(firstMessage(NO_NETWORK), "No connection."))
	withOnline(true, () => assert.equal(firstMessage(NO_NETWORK), "Could not reach the server."))
	withOnline(false, () =>
		assert.equal(
			firstMessage(new Error("NetworkError when attempting to fetch resource.")),
			"No connection."
		)
	)
	withOnline(false, () =>
		assert.equal(firstMessage(new TypeError("Load failed")), "No connection.")
	)
})

test("a form save that never reached the server says the form is kept, and may not have been sent", () => {
	withOnline(false, () =>
		assert.equal(
			saveFailedSentence(NO_NETWORK),
			"You are offline, so it may not have been sent. What you typed is still here."
		)
	)
	withOnline(true, () =>
		assert.equal(
			saveFailedSentence(NO_NETWORK),
			"The server could not be reached, so it may not have been sent. What you typed is still here."
		)
	)
	assert.equal(saveFailedSentence(PERMISSION_ERROR), "Insufficient Permission for Account")
})

test("refusalText stays text-only: it imports no toast, sanitiser or markup writer", () => {
	// gToast (components/glass/toast.js) is the ONE sink that escapes; a second one here would
	// be a second place for the guarantee to drift.
	const source = readFileSync(new URL("../refusalText.js", import.meta.url), "utf8")
	assert.doesNotMatch(source, /^import /m, "no imports at all")
	assert.doesNotMatch(source, /innerHTML|safeHtml|gToast|toast\(/)
})

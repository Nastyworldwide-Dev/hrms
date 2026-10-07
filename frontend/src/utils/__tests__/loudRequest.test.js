// loudRequest.js is the thin seam every resource passes through (setConfig("resourceFetcher") in
// resourceConfig.js): it wires the real toast and the session cookie into the pieces that do the
// work. It cannot be imported under plain node or bun (its "@/components/glass/toast" import is
// Vite's alias and the toast reaches for frappe-ui), so its wiring is asserted from source, the way
// this repo does for such modules; the behaviour sits in the two modules it wires together and is
// executed there:
//   requestFailure.test.js  what a failed request deserves (silent / refused / repeat / load)
//   refusalText.test.js     a server refusal as plain words (the table of refusal shapes)
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const source = readFileSync(new URL("../loudRequest.js", import.meta.url), "utf8")
const code = source.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/[^\n]*/g, "$1")

test("callers keep importing the readers and the rejection guard from loudRequest", () => {
	// 17 components and resourceConfig.js import these names from "@/utils/loudRequest"
	assert.match(code, /export \{ firstMessage, saveFailedSentence \} from "\.\/refusalText\.js"/)
	assert.match(code, /export \{ swallowReportedRejection \} from "\.\/requestFailure\.js"/)
	assert.match(code, /export function makeLoudRequest\(/)
})

test("makeLoudRequest wires the real toast, the clock and the session cookie, and nothing else", () => {
	assert.match(code, /import \{ gToast \} from "@\/components\/glass\/toast"/)
	assert.match(code, /notify = gToast/)
	assert.match(code, /now = \(\) => Date\.now\(\)/)
	assert.match(code, /signedIn: \(\) => Boolean\(sessionUser\(\)\)/)
	assert.match(code, /makeFailureReporter\(request, \{ notify, now, signedIn/)
})

test("the seam adds no second toast sink: only glass/toast.js speaks to frappe-ui", () => {
	// gToast escapes its text (the toast renders it with v-html); a direct frappe-ui toast here
	// would skip that. The repo-wide guard is __tests__/no-unsanitised-html.test.js.
	assert.doesNotMatch(code, /from "frappe-ui|frappeUiLean|innerHTML|safeHtml/)
	for (const file of ["requestFailure.js", "refusalText.js"]) {
		const text = readFileSync(new URL(`../${file}`, import.meta.url), "utf8")
		assert.doesNotMatch(text, /from "frappe-ui|frappeUiLean|innerHTML|safeHtml|gToast/, file)
	}
})

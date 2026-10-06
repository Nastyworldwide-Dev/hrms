// R1 (alpha.37): every read that learns "the server says you are signed out" hands it to the ONE
// owner, sessionEnded() in utils/personalCache.js. None of them routes to Login on its own: that
// skipped the signed-out mark and the offline page copy (alpha.35 review).
// Each module's real source runs with its imports replaced by recorders (the Login.vue recipe), since
// the "@/" alias is Vite's and plain node cannot resolve it.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

function load(file, extra = {}) {
	const source = readFileSync(new URL(`../${file}`, import.meta.url), "utf8")
	const calls = { sessionEnded: 0, push: 0, resources: [] }
	const bindings = {
		personalCacheKey: (k) => k,
		sessionEnded: () => calls.sessionEnded++,
		router: { push: () => calls.push++, replace: () => calls.push++ },
		createResource: (options) => {
			calls.resources.push(options)
			return { options }
		},
		reactive: (v) => v,
		...extra,
	}
	const code = source
		.replace(/^import[\s\S]*?from ["'][^"']+["'];?$/gm, "")
		.replace(/^export (const|function)/gm, "$1")
	new Function(...Object.keys(bindings), code)(...Object.values(bindings))
	return calls
}

const AUTH = { exc_type: "AuthenticationError" }
const callers = [
	["user.js", "the user read"],
	["employee.js", "the employee read"],
	["employees.js", "the all-employees read", { employeeResource: { data: null } }],
]

for (const [file, label, extra] of callers) {
	test(`${label}: AuthenticationError hands over to sessionEnded once, no Login route of its own`, () => {
		const calls = load(file, extra)
		const onError = calls.resources.at(-1).onError
		onError(AUTH)
		assert.equal(calls.sessionEnded, 1)
		assert.equal(calls.push, 0)
	})

	test(`${label}: any other failure leaves the session alone`, () => {
		const calls = load(file, extra)
		const onError = calls.resources.at(-1).onError
		onError({ exc_type: "ValidationError" })
		onError(new TypeError("Failed to fetch"))
		onError(null)
		assert.equal(calls.sessionEnded, 0)
		assert.equal(calls.push, 0)
	})

	test(`${label}: imports sessionEnded from the one owner`, () => {
		const source = readFileSync(new URL(`../${file}`, import.meta.url), "utf8")
		assert.match(source, /import \{[^}]*\bsessionEnded\b[^}]*\} from "@\/utils\/personalCache"/)
		assert.doesNotMatch(source.replace(/\/\/[^\n]*/g, ""), /router\.push|"\/login"|name: "Login"/)
	})
}

import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) =>
	readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

// Observed live 2026-08-19: the LOGIN page toasted three "not permitted"
// errors before anyone typed a thing — module-scope auto resources fire for
// Guest sessions too, the server rightly answers 403, and the loud-error
// seam reports it to exactly the wrong audience. The cure is a pair, and
// each half is useless without the other:
//   * the guest gate in resourceConfig holds non-login resources for Guests
//     (pending, silent) instead of sending them;
//   * login performs a FULL page load, so everything the gate held
//     re-evaluates and fetches with the session cookie present.
// Drop the reload and every gate-held resource stays dead after an in-page
// login; drop the gate and the login page toasts again.

test("the seam holds non-login resources for guests", () => {
	const source = read("../src/resourceConfig.js")
	assert.match(source, /guestQuiet/)
	assert.match(source, /GUEST_URLS/)
	assert.match(source, /new Promise\(\(\) => \{\}\)/)
})

test("the login page's own guest resources stay allowed", () => {
	const source = read("../src/resourceConfig.js")
	assert.match(source, /get_user_pass_login_disabled/)
	assert.match(source, /oauth_providers/)
})

test("login performs a full page load, not a router hop", () => {
	const source = read("../src/data/session.js")
	assert.match(source, /window\.location\.replace\("\/hrms"\)/)
	assert.doesNotMatch(
		source,
		/handleLogin[\s\S]{0,300}router\.replace\(\{ path/,
		"router.replace after login leaves every gate-held resource dead"
	)
})

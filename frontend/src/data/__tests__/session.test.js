// How session.js logs a person out: the phone is handed back FIRST (auth hunt AU-1, 5 Oct 2026).
// The behaviour of the hand-back itself is tested in utils/__tests__/handBackPhone.test.js.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

test("logging out unsubscribes this phone for the person leaving, before the cookie goes", async () => {
	const session = readFileSync(fileURLToPath(new URL("../session.js", import.meta.url)), "utf8")
	const logout = session.slice(session.indexOf("logout: createResource"))
	assert.match(logout, /handBackPhone\(window\.frappePushNotification\)/)
	// frappe-ui awaits `validate` but NOT `beforeSubmit`: only `validate` guarantees the unsubscribe
	// finishes before the logout request ends the session it needs
	assert.match(logout, /async validate\(\) \{\s*await handBackPhone/)
	assert.doesNotMatch(
		logout.replace(/\/\/[^\n]*/g, ""),
		/beforeSubmit/,
		"code only: the comment explains why"
	)
})

test("a Log out that fails clears its mark, so a later expired session still says 'signed out'", () => {
	const session = readFileSync(fileURLToPath(new URL("../session.js", import.meta.url)), "utf8")
	const logout = session.slice(session.indexOf("logout: createResource"))
	// the mark is set in validate(), before the request; frappe-ui runs onError for a failed request
	assert.match(logout, /onError\(\) \{\s*clearLoggingOut\(\)/)
	assert.match(session, /import \{[^}]*\bclearLoggingOut\b[^}]*\} from "@\/utils\/personalCache"/)
})

// Owner approved 27 Oct 2026 (review of bcfbeaa8e): the remembered placeholder heights are kept
// under `hrms:ph:<block>:<email>`; a shared phone must not keep the last person's email.
test("logout forgets every remembered placeholder height", () => {
	const session = readFileSync(fileURLToPath(new URL("../session.js", import.meta.url)), "utf8")
	assert.match(session, /import \{ forgetAllHeights \} from "@\/utils\/placeholderHeight"/)
	assert.match(session, /await clearPersonalCaches\(session\.user\)\s*forgetAllHeights\(\)/)
})

// Security review of e23b473b8: only the explicit Log out forgot the heights. A session that ends
// on its own (personalCache.sessionEnded, the reload onto Login) and a new login on the same phone
// also leave the previous person behind; both already clear the page copy, so both forget the
// heights beside it.
test("every way a person leaves forgets the remembered heights", () => {
	const session = readFileSync(fileURLToPath(new URL("../session.js", import.meta.url)), "utf8")
	assert.match(session, /announceSessionChange\(\)[\s\S]{0,200}?forgetAllHeights\(\)\s*await clearCachedPages\(\)/)
	const cache = readFileSync(fileURLToPath(new URL("../../utils/personalCache.js", import.meta.url)), "utf8")
	const ended = cache.slice(cache.indexOf("export function sessionEnded"))
	assert.match(ended, /forgetAllHeights\(\)\s*leavePage\(/)
	assert.match(cache, /import \{ forgetAllHeights \} from "\.\/placeholderHeight\.js"/)
})

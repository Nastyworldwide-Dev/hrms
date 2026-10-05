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

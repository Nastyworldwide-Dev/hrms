// The check-in submit path had a cul-de-sac tests never hit: a punch that
// FAILS after the selfie was captured left cameraStatus stuck at "submitting"
// (Confirm button = permanent un-tappable spinner over a dead black camera),
// and the fire-and-forget submit armed the 60s duplicate guard even on failure,
// silently blocking retry. These pin the three fixes against regression.
// Source-asserted because the node runner does not compile SFCs.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../CheckInPanel.vue", import.meta.url)), "utf8")

test("the punch is awaited, not fire-and-forget", () => {
	assert.match(src, /await punchCheckin\.submit\(/, "punch must be awaited so failure is observable")
})

test("the duplicate guard arms only on a successful punch", () => {
	// runSubmitLog returns a success boolean; submitLog gates lastSubmit on it.
	assert.match(src, /if \(ok\) lastSubmit\.value = \{ action: logType, at: Date\.now\(\) \}/, "lastSubmit must arm only when ok")
	assert.match(src, /return punchOk/, "runSubmitLog must report success/failure")
})

test("session staleness parses Frappe datetimes iOS-safely (space -> T)", () => {
	// new Date("YYYY-MM-DD HH:mm:ss") is Invalid Date on Safari, which made
	// every open IN look stale and spawned duplicate sessions on check-out.
	assert.match(src, /String\(checkinTime\)\.replace\(" ", "T"\)/, "must normalise the space to T before new Date")
})

test("a failed punch frees the frozen button by resetting the camera", () => {
	// scope to the PUNCH submit block (there is an earlier geolocation onError).
	const punchIdx = src.indexOf("await punchCheckin.submit(")
	assert.ok(punchIdx > 0, "punch submit exists")
	const punchBlock = src.slice(punchIdx, punchIdx + 3000)
	// onError must un-stick cameraStatus so the Confirm button leaves pending.
	assert.match(punchBlock, /cameraStatus\.value = "idle"/, "punch onError must reset cameraStatus out of 'submitting'")
	// and it must never fail silently — a message-less error still toasts.
	assert.match(punchBlock, /error\?\.messages\?\.length/, "punch onError must fall back to a message when the error carries none")
})

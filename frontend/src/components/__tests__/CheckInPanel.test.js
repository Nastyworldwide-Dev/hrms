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
	assert.match(
		src,
		/await punchCheckin\.submit\(/,
		"punch must be awaited so failure is observable"
	)
})

test("the duplicate guard arms only on a successful punch", () => {
	// runSubmitLog returns a success boolean; submitLog gates lastSubmit on it.
	assert.match(
		src,
		/if \(ok\) lastSubmit\.value = \{ action: logType, at: Date\.now\(\) \}/,
		"lastSubmit must arm only when ok"
	)
	assert.match(src, /return punchOk/, "runSubmitLog must report success/failure")
})

test("session staleness parses Frappe datetimes iOS-safely (space -> T)", () => {
	// new Date("YYYY-MM-DD HH:mm:ss") is Invalid Date on Safari, which made
	// every open IN look stale and spawned duplicate sessions on check-out.
	assert.match(
		src,
		/String\(checkinTime\)\.replace\(" ", "T"\)/,
		"must normalise the space to T before new Date"
	)
})

test("a failed punch frees the frozen button by resetting the camera", () => {
	// scope to the PUNCH submit block (there is an earlier geolocation onError).
	const punchIdx = src.indexOf("await punchCheckin.submit(")
	assert.ok(punchIdx > 0, "punch submit exists")
	const errorIdx = src.indexOf("onError(error) {", punchIdx)
	const endIdx = src.indexOf("\n\t\t},\n\t})", errorIdx)
	assert.ok(errorIdx > punchIdx, "punch error callback exists")
	assert.ok(endIdx > errorIdx, "punch error callback has a closing boundary")
	const punchBlock = src.slice(errorIdx, endIdx)
	// onError must un-stick cameraStatus so the Confirm button leaves pending.
	assert.match(
		punchBlock,
		/cameraStatus\.value = "idle"/,
		"punch onError must reset cameraStatus out of 'submitting'"
	)
	// and it must never fail silently — a message-less error still toasts.
	assert.match(
		punchBlock,
		/error\?\.messages\?\.length/,
		"punch onError must fall back to a message when the error carries none"
	)

	const cameraStatus = { value: "submitting" }
	const notices = []
	let restarts = 0
	const onError = new Function(
		"generation",
		"geoGeneration",
		"cameraStatus",
		"startCamera",
		"toast",
		"__",
		"actionLabel",
		"firstMessage",
		`return ({ ${punchBlock} } }).onError`
	)(
		1,
		1,
		cameraStatus,
		() => restarts++,
		(notice) => notices.push(notice),
		(text) => text,
		"Check-in",
		// the shared reader (utils/loudRequest): first server message, plain text
		(error, fallback) => error?.messages?.[0] || fallback
	)
	onError({})
	assert.equal(cameraStatus.value, "idle")
	assert.equal(restarts, 1)
	assert.equal(notices.length, 1)
	assert.match(notices[0].text, /failed.*try again/)
})

test("the button never falls back to Check In while the log reloads", () => {
	// Reported 17 Sep 2026: "they do checked in, sometimes their nadi pwa glitch
	// or show cached showing, they need to clock in again (their clock in goes
	// missing, suppose to show clock out)".
	//
	// `lastLog` answered `{}` for the whole of any reload — a socket
	// list_update, a pull-to-refresh, the app resuming, the reload after a
	// punch — and on 4G that window is seconds. `liveAction` reads `{}` as "no
	// open session" and renders **Check In** on somebody who is checked in.
	// They tap it, the server correctly records a check-OUT, and from their
	// side the check-in went missing. The stored punch was right; the label
	// lied. Holding the last row the list actually delivered keeps it honest.
	assert.match(
		src,
		/const lastKnownLog = shallowRef\(null\)/,
		"the last delivered row must be kept across a reload"
	)
	const idx = src.indexOf("const lastLog = computed(")
	assert.ok(idx > 0, "lastLog exists")
	const body = src.slice(idx, src.indexOf("\n})", idx))
	assert.doesNotMatch(
		body,
		/loading \|\| !checkins\.data\) return \{\}/,
		"a reload must not read as 'no open session'"
	)
	assert.match(body, /lastKnownLog\.value/, "lastLog must fall back to the last known row")
})

test("the punch's own answer updates the label before the reload lands", () => {
	// The held-over row fixes the label in one direction only. After a
	// check-OUT succeeds, the reload is a round trip, and until it lands the
	// held row is still the IN this punch just closed — so the button would
	// read "Check Out" to somebody who has just checked out: the same lie,
	// reversed. The punch response already carries the stored row, so use it.
	const idx = src.indexOf("async onSuccess(doc) {")
	assert.ok(idx > 0, "the punch success handler exists")
	const body = src.slice(idx, src.indexOf("checkins.reload()", idx))
	assert.match(
		body,
		/lastKnownLog\.value = doc/,
		"the stored punch must set the label before the reload is asked for"
	)
})

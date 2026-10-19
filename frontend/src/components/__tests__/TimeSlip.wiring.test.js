// A late arrival can be excused by a time slip, sent from the check-in sheet before the punch
// and from Today after it (owner, 14 Oct 2026). Source-asserted because the node runner does not
// compile SFCs (see ExpensesTable.test.js). The rules themselves are utils/__tests__/timeSlip.test.js.
// Run: cd frontend && node --test src/components/__tests__/TimeSlip.wiring.test.js
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const panel = read("../CheckInPanel.vue")
const bar = read("../NowBar.vue")
const fields = read("../TimeSlipFields.vue")

// the punch's success handler: from `async onSuccess(doc) {` to its `onError(error) {`
// (searched from onSuccess on: "onError(error)" also occurs inside describeGeolocationError(error))
const successAt = panel.indexOf("async onSuccess(doc)")
const onSuccess = panel.slice(successAt, panel.indexOf("onError(error) {", successAt))

test("the check-in sheet imports the late rule and the sender", () => {
	assert.match(panel, /import \{[^}]*\blateMinutes\b[^}]*\} from "@\/utils\/timeSlip"/)
	assert.match(panel, /import \{[^}]*\bsendTimeSlip\b[^}]*\} from "@\/utils\/timeSlip"/)
})

// the helper that sends the slip: from its declaration to the next top-level comment block
const helperAt = panel.indexOf("async function sendSlipAfterPunch(")
const helper = panel.slice(helperAt, panel.indexOf("\n}\n", helperAt))

test("the slip is sent only from the punch's success path, never before it", () => {
	assert.ok(onSuccess.length > 100, "found the punch's onSuccess")
	assert.ok(helper.length > 50, "found the sender")
	// one call to the library sender, inside the helper; one call to the helper, inside onSuccess
	assert.equal((panel.match(/\bsendTimeSlip\(/g) || []).length, 1, "one sendTimeSlip call site")
	assert.ok(helper.includes("sendTimeSlip("), "it is inside the helper")
	assert.equal(
		(panel.match(/\bsendSlipAfterPunch\(/g) || []).length,
		2,
		"declared once, called once"
	)
	assert.ok(onSuccess.includes("sendSlipAfterPunch("), "the helper is called inside onSuccess")
})

test("a slip that fails to send never blocks or undoes the punch", () => {
	// caught and toasted, never rethrown: the punch is already stored by then
	assert.match(helper, /try \{[\s\S]*await sendTimeSlip\([\s\S]*\} catch/)
	assert.doesNotMatch(helper, /throw /)
	// and not awaited by the punch: a slow upload must not hold the sheet or the approval dialog
	assert.doesNotMatch(onSuccess, /await sendSlipAfterPunch/)
})

test("a late check-in offers the slip only when the next action is a check-in", () => {
	assert.match(panel, /nextAction\.value\?\.action === "IN"/)
	assert.match(panel, /lateMinutes\(\s*new Date\(\)/)
	// the shift's end, so a night shift checked in after midnight still counts as late
	assert.match(panel, /shift\.start, shift\.late_grace, shift\.late_marking, shift\.end\)/)
})

test("the button names the slip when it goes with the check-in, and waits for the file", () => {
	assert.match(panel, /Check in and send the slip/)
	// on AND no file yet -> the Confirm button is disabled
	assert.match(
		panel,
		/slipMissingFile = computed\(\(\) => slipActive\.value && !slipFile\.value\)/
	)
	assert.match(panel, /slipActive = computed\(\(\) => minutesLate\.value > 0 && slipOn\.value\)/)
	assert.match(panel, /:disabled="cameraStatus === 'starting' \|\| !online \|\| slipMissingFile"/)
})

test("the switch and the file are cleared when the sheet closes", () => {
	const dismiss = panel.slice(panel.indexOf("function onModalDismiss"))
	assert.match(dismiss.slice(0, dismiss.indexOf("\n}\n")), /resetSlip\(\)/)
})

test("sending the slip reloads what Today reads, even when the file did not go", () => {
	assert.match(helper, /finally \{[\s\S]*nowResource\.reload\(\)/)
})

test("both screens ask in the same words, through the shared rows", () => {
	assert.match(panel, /<TimeSlipFields\b/)
	assert.match(bar, /<TimeSlipFields\b/)
	assert.match(fields, /:accept="SLIP_FILE_TYPES"/)
	assert.match(fields, /Clinic visit/)
})

test("Today says the slip's status with the one status-line rule", () => {
	assert.match(bar, /import \{[^}]*\bslipStatusLine\b[^}]*\} from "@\/utils\/timeSlip"/)
	assert.match(bar, /slipStatusLine\(slip\.value\.status/)
	assert.match(bar, /__\("Time slip"\) \}\} <span aria-hidden="true">·<\/span>/)
})

test("Today offers a slip only for a late day with none filed, and sends it for that day", () => {
	assert.match(bar, /Late today\? Add a time slip/)
	assert.match(bar, /Number\(slip\.value\?\.late_minutes\) > 0 && !slip\.value\?\.name/)
	assert.match(bar, /const slip = computed\(\(\) => data\.value\.time_slip/)
	assert.match(bar, /day: slip\.value\.day/)
	assert.match(bar, /finally \{[\s\S]*nowResource\.reload\(\)/)
})

// Design review of c9a824c15: the required file was display:none, so a keyboard or
// screen reader could never reach it, and the slip sat above the camera (mockup: below).
test("the slip file is reachable and the slip follows the camera, with its hint", () => {
	const fields = readFileSync(fileURLToPath(new URL("../TimeSlipFields.vue", import.meta.url)), "utf8")
	assert.match(fields, /class="g-sr"\s+type="file"/)
	assert.doesNotMatch(fields, /class="hidden"\s+type="file"/)
	assert.match(fields, /:has\(input:focus-visible\)/)
	assert.match(fields, /\.timeslip-file \{[^}]*position: relative/)
	const panel = readFileSync(fileURLToPath(new URL("../CheckInPanel.vue", import.meta.url)), "utf8")
	assert.ok(panel.indexOf("<GSelfiePanel") < panel.indexOf("checkin-sheet__slip\""))
	assert.match(panel, /If they do, today is not marked late/)
})

// Code review of c9a824c15: the picker offered files the server refuses, and a slip
// saved without its file had nowhere to get one.
test("the picker takes only what the server accepts", () => {
	const fields = readFileSync(fileURLToPath(new URL("../TimeSlipFields.vue", import.meta.url)), "utf8")
	assert.match(fields, /:accept="SLIP_FILE_TYPES"/)
	const util = readFileSync(fileURLToPath(new URL("../../utils/timeSlip.js", import.meta.url)), "utf8")
	assert.match(util, /SLIP_FILE_TYPES = "image\/jpeg,image\/png,application\/pdf"/)
})

test("Today offers the file for a waiting slip saved without one", () => {
	const bar = readFileSync(fileURLToPath(new URL("../NowBar.vue", import.meta.url)), "utf8")
	assert.match(bar, /slip\.value\.status === "Open" && !slip\.value\.has_file/)
	assert.match(bar, /if \(slipNeedsFile\.value\) await attachSlipFile\(slip\.value\.name, slipFile\.value\)/)
	const api = readFileSync(fileURLToPath(new URL("../../../../hrms/api/now.py", import.meta.url)), "utf8")
	assert.match(api, /"has_file": bool\(/)
})

// alpha.48 "Later", done in alpha.57: once a file is picked the row says so with a tick, and that a
// tap replaces it; the empty row keeps "Required" and the upload icon.
test("a picked slip file shows a tick and Tap to replace", () => {
	assert.match(fields, /<Check\b[^>]*v-if="file"/)
	assert.match(fields, /<Upload\b[^>]*v-else/)
	assert.match(fields, /__\("Tap to replace"\)/)
})

// Design review of 873f5e139: the input's aria-label replaced the row's text, so VoiceOver never
// said which file was picked, or that one is required.
test("the file input names the picked file to a screen reader", () => {
	assert.match(fields, /__\('Add a file, \{0\}\. Tap to replace', \[file\.name\]\)/)
	assert.match(fields, /__\('Add a file, required'\)/)
})

// alpha.48 "Later": Today's slip line changes on its own (Waiting -> Approved) while Home is open;
// as a status region a screen reader hears the change, as the check-in sheet's pill already does.
test("Today's slip line is a status a screen reader hears change", () => {
	// the region is mounted before the line, so its first appearance is heard (design review of eeb854f8c)
	assert.match(bar, /<div class="g-now__slip-live" role="status">\s*<p v-if="slipLine" class="g-now__slip"/)
	assert.match(bar, /\.g-now__slip-live \{\s*display: contents;/)
	assert.match(panel, /class="checkin-sheet__slip-pill" role="status"/)
})

// Review of 2c32b184d (Critical): the sheet files the slip on the shift's own day.
test("the check-in sheet files the slip on the shift's own day", () => {
	assert.match(helper, /day: slipDay\(/)
	// the site's date with the site's clock (review of 10781a529), never the phone's
	assert.match(helper, /wallClock\(nowResource\.data\?\.time\)/)
})

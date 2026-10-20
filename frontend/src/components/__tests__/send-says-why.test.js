// alpha.60 sweep: three Send buttons went dead with no reason (GButton swallows
// a disabled tap). Every disabled state shows a visible reason at the action,
// linked by aria-describedby. Source-asserted (no SFC compile in node).
// Run: cd frontend && node --test src/components/__tests__/send-says-why.test.js
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (name) => {
	const src = readFileSync(fileURLToPath(new URL(`../${name}.vue`, import.meta.url)), "utf8")
	return { src, template: src.slice(0, src.indexOf("<script")) }
}

test("RemoteCheckinDialog: an empty reason says so at Send", () => {
	const { template } = read("RemoteCheckinDialog")
	assert.match(template, /id="remote-checkin-hint"/)
	assert.match(template, /__\("Write a reason to send\."\)/)
	assert.match(template, /:aria-describedby="[^"]*remote-checkin-hint/)
})

test("CheckInPanel: a slip with no file says so at Confirm", () => {
	const { src, template } = read("CheckInPanel")
	assert.match(template, /id="checkin-confirm-hint"[^>]*>\s*\{\{ confirmHint \}\}/)
	assert.match(template, /:aria-describedby="[^"]*checkin-confirm-hint/)
	const hint = src.slice(src.indexOf("const confirmHint"), src.indexOf("const confirmHint") + 300)
	assert.match(hint, /__\("You need signal to check in\."\)/)
	assert.match(hint, /__\("Add the time slip file to continue\."\)/)
})

test("CheckInPanel: a camera that never starts stops blocking Confirm", () => {
	const { src } = read("CheckInPanel")
	const at = src.indexOf("async function startCamera")
	const body = src.slice(at, src.indexOf("function stopCamera", at))
	assert.match(body, /setTimeout\(/)
	assert.match(body, /CAMERA_START_TIMEOUT_MS/)
	assert.match(body, /cameraStatus\.value !== "starting"\) return/)
})

test("NowBar: a time slip with no file says so at Send", () => {
	const { template } = read("NowBar")
	assert.match(template, /id="nowbar-slip-hint"/)
	assert.match(template, /__\("Add the time slip file to send\."\)/)
	assert.match(template, /:aria-describedby="[^"]*nowbar-slip-hint/)
})

test("CheckInPanel: every disabled Confirm/check-in state is linked to its reason", () => {
	const { src, template } = read("CheckInPanel")
	assert.match(template, /id="checkin-camera-msg"/)
	assert.match(template, /'checkin-camera-msg'/)
	assert.match(template, /:aria-describedby="online \? undefined : 'checkin-offline-hint'"/)
	assert.match(template, /id="checkin-offline-hint"/)
	const stop = src.slice(
		src.indexOf("function stopCamera"),
		src.indexOf("function stopCamera") + 120
	)
	assert.match(stop, /clearTimeout\(cameraStartTimer\)/)
})

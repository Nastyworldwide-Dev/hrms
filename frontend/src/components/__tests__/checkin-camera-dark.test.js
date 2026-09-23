// Plan P1-5 (owner screenshot, 23 Sep): in dark mode the check-in camera
// box was a white slab. It was painted with --g-ink, the TEXT colour, which
// is near-white in dark mode; its message used --g-bg, which is near-black
// there — dark text on white. A viewfinder is a dark frame in both themes.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../CheckInPanel.vue", import.meta.url)), "utf8")

test("the camera frame is dark in both themes, its words light", () => {
	const frame = src.slice(src.indexOf(".checkin-sheet__camera {"), src.indexOf(".checkin-sheet__video"))
	assert.doesNotMatch(frame, /var\(--g-ink\)/)
	assert.match(frame, /background: var\(--g-media-frame\);/)
	const msg = src.slice(src.indexOf(".checkin-sheet__camera-msg {"), src.indexOf("/* Live"))
	assert.match(msg, /color: var\(--g-on-media-frame\);/)
})

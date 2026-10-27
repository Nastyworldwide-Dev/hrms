// Owner, 27 Oct 2026: on a day of approved leave Home still read "Not checked in" over a lime
// Check in button. The server now says state "leave" (now.py); the bar shows the leave in its own
// colour, and the card gives no big Check in button that day (a person who comes in anyway still
// has the Check-in page).
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("the bar names the leave in the detail line and gives it the leave colour", () => {
	const bar = read("../NowBar.vue")
	assert.match(bar, /stateKey\.value === "leave" && data\.value\.state\?\.leave_type/)
	const css = read("../../theme/glass-components.css")
	assert.match(css, /\.g-now--leave \.g-now__dot \{\s*background: var\(--g-leave\);/)
})

test("the card has no Check in button on a full day of leave", () => {
	const card = read("../CheckInPanel.vue")
	assert.match(card, /const onLeave = computed\(\(\) => nowResource\.data\?\.state\?\.key === "leave"\)/)
	assert.match(card, /<GButton\s+v-if="!onLeave"\s+id="open-checkin-modal"/)
})

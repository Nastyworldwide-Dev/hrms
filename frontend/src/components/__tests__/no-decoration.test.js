// Anti-"AI slop" rules from the audit basis (S-ARROW, S-EMOJI, S-DECO; audit
// F-10 / APP-20, APP-23): an arrow on a button promises a new screen, so an
// action (check in, log in, submit) carries none; interface text has no emoji;
// the main button is a flat brand fill with no coloured glow.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8")

test("action buttons carry no arrow", () => {
	for (const file of [
		"../CheckInPanel.vue",
		"../../views/Login.vue",
		"../../views/helpdesk/TicketNew.vue",
	]) {
		assert.doesNotMatch(read(file), /<ArrowRight/, file)
	}
})

test("interface text has no emoji", () => {
	assert.doesNotMatch(read("../CheckInPanel.vue"), /\p{Extended_Pictographic}/u)
})

test("the main button is a flat brand fill with no glow", () => {
	const css = read("../../theme/glass-components.css")
	const block = css.match(/\n\.g-btn \{[^}]*\}/)[0]
	assert.doesNotMatch(block, /linear-gradient/)
	assert.doesNotMatch(block, /--g-shadow-action/)
})

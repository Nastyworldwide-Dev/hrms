import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

// Owner ruling, 23 Sep 2026: staff can turn their check-in / check-out
// reminders off on the You page. ON by default, their own setting only.
const source = readFileSync(
	fileURLToPath(new URL("../src/views/Profile.vue", import.meta.url)),
	"utf8"
)

test("the You page reads the reminder setting from the server", () => {
	assert.match(source, /url:\s*"hrms\.utils\.shift_reminders\.get_shift_reminders"/)
})

test("flipping the switch saves it through the own-setting endpoint", () => {
	assert.match(source, /url:\s*"hrms\.utils\.shift_reminders\.set_shift_reminders"/)
	const handler = source.slice(source.indexOf("function toggleReminders"))
	assert.match(handler, /setReminders\.submit\(\{\s*enabled:/, "the toggle sends the new value")
})

test("the switch is bound to the setting and ON until the server says otherwise", () => {
	// alpha.6 B3: the row text is the label; the switch is named by aria-label.
	assert.match(source, /:aria-label="__\('Shift reminders'\)"/)
	assert.match(source, /:model-value="remindersOn"/)
	assert.match(source, /@update:model-value="toggleReminders"/)
	assert.match(source, /const remindersOn = ref\(true\)/)
})

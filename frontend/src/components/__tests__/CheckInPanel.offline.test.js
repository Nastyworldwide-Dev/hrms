// Owner ruling (22 Sep): never an offline check-in. Offline, the button used
// to stay enabled — it opened the sheet and the camera, and "Confirm Check In"
// was live; the only reason on screen was the top banner (audit P0-7, measured
// with the network cut). The action is blocked, and the reason sits AT the
// action. Source-asserted because the node runner does not compile SFCs.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../CheckInPanel.vue", import.meta.url)), "utf8")
const template = src.slice(src.indexOf("<template>"), src.indexOf("<script setup>"))

function buttonTag(anchor) {
	const at = template.indexOf(anchor)
	return template.slice(template.lastIndexOf("<GButton", at), template.indexOf(">", at))
}

test("the panel reads the shared online state", () => {
	assert.match(src, /import \{ useOnline \} from "@\/composables\/useOnline"/)
	assert.match(src, /const online = useOnline\(\)/)
})

test("the check-in button is disabled offline", () => {
	assert.match(buttonTag('id="open-checkin-modal"'), /:disabled="!online"/)
})

test("the sheet's confirm button is disabled offline too (signal lost mid-sheet)", () => {
	assert.match(buttonTag("__('Confirm {0}'"), /!online/)
})

test("the reason sits under the button, in the person's words", () => {
	assert.match(
		template,
		/v-if="!online"[^>]*>\s*\{\{\s*__\("You need signal to check in\."\)\s*\}\}/
	)
})

test("submitting offline is refused in code, not only by a disabled button", () => {
	const body = src.slice(
		src.indexOf("const submitLog = async"),
		src.indexOf("\n}\n", src.indexOf("const submitLog = async"))
	)
	assert.match(body, /if \(!online\.value\)/)
})

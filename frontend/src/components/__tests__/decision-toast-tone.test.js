// Family B (25 Sep 2026 hunt): approving a late check-out whose day could NOT
// be rebuilt showed a neutral "info" banner, because the sheet dropped the
// tone decisionToast() worked out. "Approved" + "Attendance was not updated"
// must read as a warning, and a clean approval as success.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../CheckinDecisionSheet.vue", import.meta.url)), "utf8")

test("the banner carries the tone the decision earned", () => {
	assert.match(src, /variant: shown\.tone/)
	assert.doesNotMatch(src, /title: shown\.title,\s*text: shown\.text,\s*variant: "info"/)
})

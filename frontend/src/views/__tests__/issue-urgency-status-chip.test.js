// Design audit, 27 Oct 2026: the HR Issue Board drew urgency with Tailwind red/amber outline
// classes (text-red-600, text-amber-700) and the "High urgency" figure in text-red-600: colours
// outside the Glass palette, the only screen that did. GStatusChip is the one status pill (its
// six variants are contrast-measured in both themes), with the map the manpower wizard uses.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../issues/HRIssueBoard.vue", import.meta.url)), "utf8")

test("urgency is a GStatusChip with the shared colour key, never a raw palette class", () => {
	assert.doesNotMatch(src, /text-(red|amber)-\d|border-(red|amber)-\d/)
	assert.match(src, /<GStatusChip[\s\S]*?:status="URGENCY_CHIP\[issue\.urgency\]"[\s\S]*?:label="__\(issue\.urgency\)"/)
	assert.match(src, /const URGENCY_CHIP = \{ High: "rejected", Medium: "waiting", Low: "draft" \}/)
})

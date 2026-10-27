// Design audit, 27 Oct 2026: New IT ticket drew Type and Priority as raw <select>s with a
// label made of an eyebrow span, next to GInput/GTextarea on the same form. GSelect is the one
// picker: same label style as the inputs, native wheel, 44 px, chevron.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../TicketNew.vue", import.meta.url)), "utf8")
const template = src.slice(0, src.indexOf("<script"))

test("Type and Priority are GSelects, not raw selects", () => {
	assert.doesNotMatch(template, /<select\b/)
	assert.match(template, /<GSelect[\s\S]*?v-model="form\.ticket_type"[\s\S]*?\/>/)
	assert.match(template, /<GSelect[\s\S]*?v-model="form\.priority"[\s\S]*?\/>/)
	assert.match(src, /import GSelect from "@\/components\/glass\/GSelect\.vue"/)
})

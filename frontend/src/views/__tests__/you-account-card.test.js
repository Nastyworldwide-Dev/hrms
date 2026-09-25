// alpha.8: the You page's person, as iOS Settings draws the account (owner's
// iOS 26 Settings, measured at 3x): a 60 pt CIRCLE avatar, the name 22 pt
// bold beside it, the details under it, all inside one grouped row. Nadi drew
// a 72 pt square and a 20 pt name loose on the page, wrapping to two lines.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const src = readFileSync(fileURLToPath(new URL("../Profile.vue", import.meta.url)), "utf8")

test("the account is a grouped row with a 60 pt circle", () => {
	assert.match(src, /class="g-form-group g-account"/)
	assert.match(src, /<GAvatar[\s\S]{0,160}:size="60"[\s\S]{0,40}round/)
	assert.match(src, /class="g-account__name"/)
})

test("manager and shift are label/value rows in the same group, not loose lines", () => {
	const group = src.slice(src.indexOf('class="g-form-group g-account"'), src.indexOf("<GListPanel"))
	assert.match(group, /__\("Manager"\)/)
	assert.match(group, /__\("Shift"\)/)
	assert.doesNotMatch(src, /Your manager is \{0\}/)
})

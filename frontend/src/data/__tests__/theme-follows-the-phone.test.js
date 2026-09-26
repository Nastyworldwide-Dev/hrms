// alpha.12 R4 (owner ruling, 26 Sep 2026). Apple (dark-mode): "Avoid offering
// an app-specific appearance setting. An app-specific appearance mode option
// creates more work for people because they have to adjust more than one
// setting to get the appearance they want." The app follows the phone.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const profile = read("../../views/Profile.vue")
const theme = read("../theme.js")
const html = read("../../../index.html")

test("You no longer offers an Appearance picker", () => {
	assert.doesNotMatch(profile, /__\("Appearance"\)/)
	assert.doesNotMatch(profile, /setTheme/)
})

test("the app always follows the phone, and a stored Light/Dark from before is cleared", () => {
	assert.match(theme, /mode: "system"/)
	assert.match(theme, /localStorage\.removeItem\(STORAGE_KEY\)/)
	assert.match(html, /prefers-color-scheme: dark\)"\)\.matches/)
	assert.doesNotMatch(html, /m === "dark" \|\|/)
})

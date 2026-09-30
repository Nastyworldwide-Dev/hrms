// Owner, 30 Sep 2026: "theme switching is missing" -> bring it back in You.
// This reverses the alpha.12 R4 ruling (follow the phone only). You has an
// Appearance row with Light / Dark / Automatic; the choice is remembered, and
// the boot script paints it before first paint so a chosen Dark never flashes
// light. Storage that throws must not break the app.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")
const store = read("../theme.js")
const you = read("../../views/Profile.vue")
const html = read("../../../index.html")

test("You offers Appearance with Light, Dark and Automatic", () => {
	assert.match(you, /__\("Appearance"\)/)
	assert.match(you, /:options="THEME_OPTIONS"/)
	assert.match(you, /@update:model-value="setTheme"/)
	assert.match(store, /THEME_MODES = \["light", "dark", "system"\]/)
})

test("the choice is remembered, never cleared on load", () => {
	assert.doesNotMatch(store, /localStorage\.removeItem\(STORAGE_KEY\)/)
	assert.match(store, /localStorage\.setItem\(STORAGE_KEY, mode\)/)
	assert.match(store, /mode: readMode\(\)/)
})

test("a stored Light or Dark is painted before first paint", () => {
	assert.match(html, /m === "dark" \|\|/)
	assert.match(html, /m === "system" && matchMedia/)
})

test("storage that throws does not break the theme", () => {
	const readMode = store.slice(store.indexOf("function readMode"), store.indexOf("export const theme"))
	assert.match(readMode, /try \{[\s\S]*catch \{[\s\S]*return "system"/)
	const set = store.slice(store.indexOf("export function setTheme"))
	assert.match(set.slice(0, set.indexOf("startViewTransition")), /try \{\s*localStorage\.setItem/)
})

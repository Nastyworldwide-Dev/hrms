// Owner ruling, 23 Sep 2026: no background blobs. The three-blob "light
// field" behind every page was decoration with no job (audit APP-19, S-DECO),
// it made two blurred layers animate during every page push, and it cost a
// whole contrast gate to keep text readable over it. The solid page ground
// stays: it is the fix for pages painting through each other mid-transition.
import { test } from "node:test"
import assert from "node:assert/strict"
import { existsSync, readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const at = (path) => fileURLToPath(new URL(path, import.meta.url))
const read = (path) => readFileSync(at(path), "utf8")

test("no component renders a light field", () => {
	assert.equal(existsSync(at("../../components/glass/GLightField.vue")), false)
	assert.doesNotMatch(read("../../components/glass/GPage.vue"), /GLightField/)
})

test("no stylesheet styles one", () => {
	assert.doesNotMatch(read("../glass-components.css"), /\.g-lightfield/)
	assert.doesNotMatch(read("../glass.css"), /--g-field-|--g-blob-opacity/)
})

test("no token defines one", () => {
	const tokens = JSON.parse(read("../../../../design/tokens.json"))
	assert.equal(tokens.field, undefined)
	assert.equal(tokens["color-themed"]["blob-opacity"], undefined)
})

test("the solid page ground stays (it stops pages painting through each other)", () => {
	assert.match(read("../glass-components.css"), /\.ion-page\.g-page\s*\{\s*background: var\(--g-bg/)
})

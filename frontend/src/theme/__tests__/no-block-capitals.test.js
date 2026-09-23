// Block capitals slow reading and are harder with dyslexia (basis NG-CAPS,
// W-CASE, W-DYS; audit-pages PAGE-10). The labels are written in sentence
// case; the stylesheet must not turn them into capitals.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8")

test("no glass class forces capitals", () => {
	const css = read("../glass-components.css").replace(/\/\*[\s\S]*?\*\//g, "")
	assert.doesNotMatch(css, /text-transform:\s*uppercase/)
})

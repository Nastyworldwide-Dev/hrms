// alpha.14 P1: two things kept code the first screen never uses in the first
// download. Measured on the alpha.12 slow-phone profile (e2e/first-paint.mjs):
// FCP 5.68 s -> 5.28 s; main JS 492 -> 467 KB; blocking CSS 182 -> 150 KB.
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"

const read = (p) => readFileSync(fileURLToPath(new URL(p, import.meta.url)), "utf8")

test("Ionic's wrappers can be dropped when unused", () => {
	const cfg = read("../../vite.config.js")
	assert.match(cfg, /ionicPure\(\),/)
	assert.match(cfg, /moduleSideEffects: false/)
	// the `IonX.name = "IonX"` assignments kept every wrapper alive
	assert.ok(cfg.includes(String.raw`/^(Ion[A-Za-z]+)\.name = ("Ion[A-Za-z]+");$/gm`))
})

test("Tailwind scans only the frappe-ui components the app renders", () => {
	const tw = read("../../tailwind.config.js")
	assert.doesNotMatch(tw, /frappe-ui\/src\/components\/\*\*\/\*/)
	assert.match(tw, /frappe-ui\/src\/components\/\{ErrorMessage\.vue,toast\.js,Toast\.vue,TextEditor/)
})
